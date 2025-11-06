## Overview

This project aims to solve the problem of generating accurate animated videos from 
just the prompt (uses manim-ce under then hood with agentic pipeline using langgraph).


## Highlights

- Modification of LLM generated code iteratively with specialized agents for 
  planning of steps, evaluation of code.

- Embedded documentation, code snippets/examples from manim community codebase
  with implementation of hierarchical chunking to prevent coding agent from hallucination.

- Implemented docker sandbox execution for llm generated python code (with manim-ce).

- Self hosted coding embedding model (qwen3-embedding:0.6b) in HF Spaces.


## System Design

![System Design](/assets/final-architecture.png)

## Setup

- Clone the repository
  ```bash
  git clone https://github.com/MSVelan/enginimate.git
  ```

- Install uv. [Guide](https://docs.astral.sh/uv/getting-started/installation/)

- Copy .env.example and modify variables
  ```bash
  cp .env.example .env
  ```

- Run setup.sh
  ```bash
  source setup.sh
  ```
