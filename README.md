## Overview

This project aims to solve the problem of generating accurate animated videos from 
just the prompt (uses manim-ce under the hood with agentic pipeline using langgraph).


## Highlights

- Iterative modification of LLM generated code with specialized agents for 
  clear planning and evaluation based on appropriate criterion.

- Embedded documentation, code snippets/examples from manim community codebase
  with implementation of hierarchical chunking to prevent coding agent from hallucination.  

- Implemented docker sandbox execution for llm generated python code (with manim-ce) 
  and shifted to execution in self hosted VM (inside docker container).

- Self hosted code embedding model (qwen3-embedding:0.6b) in HF Spaces.

- Render the video using Github Actions and upload to cloudinary.

- Setup cron job to fetch cleanup the videos of last 30 minutes to stay 
  within storage limits of Cloudinary free tier.


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

- Start the backend server
  ```bash
  python3 backend/routes/main.py
  ```