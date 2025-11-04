## Overview

This project aims to solve the problem of generating accurate animated videos from 
just the prompt (uses manim-ce under then hood with agentic pipeline using langgraph).


## Highlights

- Self hosted(HF Spaces) coding embedding model (qwen3-embedding:0.6b) and
  hierarchical chunking of code snippets and documentation from manim-ce codebase for RAG implemenation.


## System Design

![System Design](/assets/final-architecture.png)

## Setup

- Install uv. [Guide](https://docs.astral.sh/uv/getting-started/installation/)

- Copy .env.example and modify variables
    ```bash
    cp .env.example .env
    ```

- Run setup.sh
    ```bash
    source setup.sh
    ```
