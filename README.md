## Overview

This project aims to solve the problem of generating accurate animated videos from 
just the prompt (uses manim-ce under the hood with agentic pipeline using langgraph).

Checkout the website: https://enginimate.vercel.app/

Link to frontend repository: https://github.com/MSVelan/enginimate-frontend

Link to software design document: https://msvelan.netlify.app/p/design-document-enginimate/



## Highlights

- Iterative modification of LLM generated code with specialized agents for 
  clear planning and evaluation based on appropriate criterion.

- Embedded documentation, code snippets/examples from manim community codebase
  with implementation of hierarchical chunking to prevent coding agent from hallucination.  

- Implemented docker sandbox execution for llm generated python code (with manim-ce) and 
  later self-hosted FastAPI execution service for scalable Manim code validation. 

- Self hosted code embedding model (qwen3-embedding:0.6b) in HF Spaces to support code 
  and documentation retrieval.

- Set up a distributed rendering pipeline: Langgraph backend -> render service 
  (deployed in render.com) -> Trigger job in Github Actions using repository dispatch.

- Automated lifecycle management using a scheduled cleanup service 
  (cron + FastAPI + SQL) to keep storage usage within free-tier constraints.


## System Design

![System Design](/assets/final-architecture.png)

Checkout the full system design document: [SDD](https://msvelan.netlify.app/p/design-document-enginimate/)

### Langgraph workflow

![Langgraph workflow](/assets/workflow.png)

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

- Start the backend server
  ```bash
  python3 backend/routes/main.py
  ```