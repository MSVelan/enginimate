import re
import os
import asyncio
import concurrent.futures

from tenacity import retry, stop_after_attempt, wait_fixed
from textwrap import dedent
from typing import List, Tuple
from langchain_community.document_loaders import UnstructuredRSTLoader
from langchain_text_splitters import (
    Language,
    RecursiveCharacterTextSplitter,
)
from langchain_core.documents import Document
from langchain_postgres import PGVectorStore
from langchain_postgres import PGEngine
from dotenv import load_dotenv

from backend.workflow.utils.hf_space_wrapper import HFSpaceWrapper

load_dotenv()

MANIM_DIR = os.getenv("MANIM_DIR")

hf_space = HFSpaceWrapper()  # my wrapper which provides Embeddings

MAX_TOKENS = 1000  # max tokens for documentation
MAX_TOKENS_PY = 2000  # max tokens in py files
MAX_TOKENS_PY_EXAMPLES = 500  # max tokens for py code snippets in rst files

base_files = [
    "docs/source/guides/deep_dive.rst",
    "docs/source/guides/using_text.rst",
    "docs/source/guides/configuration.rst",
    "docs/source/tutorials/building_blocks.rst",
    "docs/source/tutorials/quickstart.rst",
    "docs/source/examples.rst",
    "docs/source/reference.rst",
    "example_scenes/basic.py",
    "example_scenes/advanced_tex_fonts.py",
    "example_scenes/opengl.py",
]

base_dir_walk = ["docs/source/reference_index/"]


async def _get_vector_store():
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT")
    TABLE_NAME = os.getenv("TABLE_NAME")

    CONNECTION_STRING = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_HOST}"
        f":{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    pg_engine = PGEngine.from_connection_string(url=CONNECTION_STRING)

    # NOTE: table is already created, just connecting to it.
    # NOTE: can provide k value here
    store = await PGVectorStore.create(
        engine=pg_engine,
        table_name=TABLE_NAME,
        # schema_name=SCHEMA_NAME,
        embedding_service=hf_space,
    )
    return store


async def ingest_docs():
    abs_files = [os.path.join(MANIM_DIR, file) for file in base_files]
    for base_directory_path in base_dir_walk:
        directory_path = os.path.join(MANIM_DIR, base_directory_path)
        for root, _, filenames in os.walk(directory_path):
            for filename in filenames:
                abs_files.append(os.path.join(root, filename))

    doc_ids = []

    with concurrent.futures.ProcessPoolExecutor(11) as executor:
        future_to_file = {
            executor.submit(_get_all_documents, file): file for file in abs_files
        }
        for future in concurrent.futures.as_completed(future_to_file):
            file = future_to_file[future]
            try:
                file_documents = future.result()

                # NOTE: below can be handled separately using asyncio.gather,
                # but server can't handle many parallel requests

                # Batch in sequence of 10 to avoid any issues from server
                n = len(file_documents)
                for i in range(0, n, 10):
                    file_doc_ids = await _reliable_aadd_documents(
                        file_documents[i : i + 10]
                    )
                    doc_ids.extend(file_doc_ids)
            except Exception as exc:
                print("%r generated an exception: %s" % (file, exc))
            else:
                print(
                    "Embedded %r file- contains %d Document objects, \
added %d objects to store"
                    % (file, len(file_documents), n)
                )
    return doc_ids


@retry(
    stop=stop_after_attempt(3),  # Try up to 3 times
    wait=wait_fixed(1),  # Wait 1 second between retries
)
async def _reliable_aadd_documents(docs):
    """Retries aadd_documents if it hits a connection closure error."""
    store = await _get_vector_store()
    ids = await store.aadd_documents(docs)
    return ids


def _get_all_documents(file) -> None:
    """Returns Langchain Document objects for chunks in the file.
    Currently supports only rst and py files"""
    _, ext = os.path.splitext(file)
    file_docs = []
    if ext == ".rst":
        loader = UnstructuredRSTLoader(file_path=file, mode="elements")
        docs = loader.load()
        grouped_docs = _get_documentation_group_by_title(docs)
        chunked_docs = _chunk_documentation(grouped_docs)
        rst_text = ""
        with open(file) as f:
            rst_text = f.read()
        code_blocks = _get_code_blocks(rst_text)
        chunked_code_blocks = _chunk_code_blocks(
            code_blocks, file, MAX_TOKENS_PY_EXAMPLES
        )
        summary_blocks = _get_summary_blocks(rst_text)
        summary_docs = _get_summary_documents(summary_blocks, file)
        file_docs = chunked_docs + chunked_code_blocks + summary_docs
    elif ext == ".py":
        content = ""
        with open(file) as f:
            content = f.read()
        python_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.PYTHON, chunk_size=MAX_TOKENS_PY, chunk_overlap=0
        )
        file_docs = python_splitter.create_documents([content])
        for doc in file_docs:
            doc.metadata.update(
                {"source": file, "filename": os.path.basename(file), "type": "code"}
            )
    return file_docs


def _get_code_blocks(rst_text: str):
    """Extract all manim directives"""
    pattern = re.compile(
        r"""(?mx)                                # multiline + verbose
        ^\.\.\s+manim::\s+(?P<cls_name>\S+)\s*\n # directive line with class name
        (?P<options>(?:[ ]{4,}:[^\n]*\n)*)       # option lines (4+ spaces, start with :)
        (?:[ ]*\n)                               # blank line between options and code
        (?P<code>(?:[ ]{4,}[^\n]*\n|[ ]*\n)+)    # lines with 4+ spaces OR empty lines
        """
    )

    blocks: List[Tuple[str, str, List[str]]] = []

    for m in pattern.finditer(rst_text):
        cls_name = m.group("cls_name")
        raw_opts = m.group("options")
        # Extract, clean options and filter only references
        opts = [
            line.strip()
            for line in raw_opts.splitlines()
            if line.strip().startswith(":ref")
        ]
        raw_code = m.group("code")
        code = dedent(raw_code).rstrip("\n")
        blocks.append((cls_name, code, opts))

    return blocks


def _chunk_code_blocks(blocks, source, max_tokens=MAX_TOKENS_PY_EXAMPLES) -> list:
    """Returns list of Document object chunks for given blocks"""

    if not blocks:
        return []

    filename = os.path.basename(source)

    def get_str(block: tuple):
        """Returns page content for the manim block object"""
        _, code, opts = block
        content = ""
        if opts:
            content = "References:\n"
            for o in opts:
                if o:
                    content += f"  {o}\n"
        content += "Code:\n"
        content += f"{code}"
        return content

    def get_rolling_window_doc(rolling_window: str, references):
        """Returns Langchain Document object for rolling window chunk"""
        rolling_doc = Document(
            page_content=rolling_window,
            metadata={"source": source, "filename": filename, "type": "code"},
        )
        ref_classes = " ".join(references["ref_classes"])
        ref_functions = " ".join(references["ref_functions"])
        ref_methods = " ".join(references["ref_methods"])
        rolling_doc.metadata.update(
            {
                "ref_classes": ref_classes,
                "ref_functions": ref_functions,
                "ref_methods": ref_methods,
            }
        )
        return rolling_doc

    def update_references(cur_references, block):
        _, _, opts = block
        if opts:
            for o in opts:
                _, pred, ref_names = o.split(":")
                ref_names = ref_names.strip()
                ref_names = set(ref_names.split())  # set of unique references
                if pred == "ref_classes":
                    ns = cur_references["ref_classes"].union(ref_names)
                    cur_references["ref_classes"] = ns
                elif pred == "ref_functions":
                    ns = cur_references["ref_functions"].union(ref_names)
                    cur_references["ref_functions"] = ns
                elif pred == "ref_methods":
                    ns = cur_references["ref_methods"].union(ref_names)
                    cur_references["ref_methods"] = ns

    new_groups = []
    rolling_window = get_str(blocks[0])
    cur_size = len(rolling_window)
    cur_references = {
        "ref_classes": set(),
        "ref_functions": set(),
        "ref_methods": set(),
    }
    update_references(cur_references, blocks[0])

    for i in range(1, len(blocks)):
        cur_st = get_str(blocks[i])
        if cur_size + len(cur_st) > max_tokens:
            rolling_window_doc = get_rolling_window_doc(rolling_window, cur_references)
            new_groups.append(rolling_window_doc)
            rolling_window = cur_st
            cur_references.update(dict.fromkeys(cur_references, set()))
        else:
            rolling_window += "\n\n"
            rolling_window += cur_st
            update_references(cur_references, blocks[i])

    if rolling_window:
        rolling_window_doc = get_rolling_window_doc(rolling_window, cur_references)
        new_groups.append(rolling_window_doc)

    return new_groups


def _get_documentation_group_by_title(docs):
    grouped_docs = []
    depth2title_map = {}
    current_section = None
    for doc in docs:
        if doc.metadata["category"] == "UncategorizedText":
            continue
        if doc.metadata["category"] == "Title":
            if current_section:
                grouped_docs.append(current_section)
            current_title = doc.page_content
            category_depth = doc.metadata["category_depth"]
            section_title = ""
            if category_depth >= 1:
                for depth in range(category_depth):
                    section_title += depth2title_map.get(depth, "") + " > "
            current_section = {
                "title": section_title + current_title,
                "content": [],
                "source": doc.metadata["source"],
                "filename": doc.metadata["filename"],
            }
            # source and filename are metadata
            depth2title_map[category_depth] = current_title
        else:
            current_section["content"].append(doc.page_content)
    if current_section:
        grouped_docs.append(current_section)

    return grouped_docs


def _chunk_documentation(grouped_docs, max_tokens=MAX_TOKENS) -> list:
    """Returns list of Document object chunks for given grouped_docs"""

    if not grouped_docs:
        return []

    def get_str(d: dict):
        """Returns page content for the grouped_docs object"""
        return "Title: " + d["title"] + "\n" + "\n".join(d["content"])

    def get_rolling_window_doc(rolling_window: str):
        """Returns Langchain Document object for rolling window chunk"""
        rolling_doc = Document(
            page_content=rolling_window,
            metadata={
                "source": source,
                "filename": filename,
                "type": "documentation",
            },
        )
        return rolling_doc

    source = grouped_docs[0]["source"]
    filename = grouped_docs[0]["filename"]
    new_groups = []
    rolling_window = get_str(grouped_docs[0])
    cur_size = len(rolling_window)
    base_title = grouped_docs[0]["title"]

    for i in range(1, len(grouped_docs)):
        cur_st = get_str(grouped_docs[i])
        cur_title = grouped_docs[i]["title"]
        if cur_title.startswith(base_title):
            if cur_size + len(cur_st) > max_tokens:
                rolling_window_doc = get_rolling_window_doc(rolling_window)
                rolling_window_doc.metadata.update({"title": base_title})
                new_groups.append(rolling_window_doc)
                rolling_window = cur_st
            else:
                rolling_window += "\n\n"
                rolling_window += cur_st
        else:
            rolling_window_doc = get_rolling_window_doc(rolling_window)
            rolling_window_doc.metadata.update({"title": base_title})
            new_groups.append(rolling_window_doc)
            rolling_window = cur_st
            base_title = cur_title

    if rolling_window:
        rolling_window_doc = get_rolling_window_doc(rolling_window)
        rolling_window_doc.metadata.update({"title": base_title})
        new_groups.append(rolling_window_doc)

    return new_groups


def _get_summary_blocks(rst_text: str) -> List[Tuple[str, str]]:
    """Extract all summary/reference blocks"""
    pattern = re.compile(
        r"""(?mx)
        ^\.\.\s+(?!manim::)(?!toctree::)(?!currentmodule::)(?P<directive>\S+)\s*\n
        (?P<content>(?:[ ]{3,}[^\n]*\n|[ ]*\n)*)
        """
    )
    blocks: List[Tuple[str, str]] = []
    for m in pattern.finditer(rst_text):
        directive = m.group("directive")
        raw_content = m.group("content")
        content = dedent(raw_content).rstrip("\n")
        blocks.append((directive, content))
    return blocks


def _get_summary_documents(blocks: List[Tuple[str, str]], source: str):
    """Creates langchain Document objects for each block"""
    docs = []
    filename = os.path.basename(source)
    for directive, content in blocks:
        t = directive.rstrip(":")
        doc = Document(
            content,
            metadata={
                "type": "summary",
                "supplement": t,
                "source": source,
                "filename": filename,
            },
        )
        docs.append(doc)
    return docs


if __name__ == "__main__":
    doc_ids = asyncio.run(ingest_docs())
    print("Ingested %d documents" % len(doc_ids))
