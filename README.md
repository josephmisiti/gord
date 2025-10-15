# Gord

Gord is Ping Intel's E&S Property Agent.

<img width="979" height="651" alt="Screenshot 2025-10-14 at 10.56.45 PM" src="https://github.com/user-attachments/assets/5bde79c4-f138-41f2-abc0-4fb22c037ca5" />

## Overview

Coming Soon.

## Quick Start

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- OpenAI API key
- Brave API key

### Installation

1. Clone the repository:

```bash
git clone git@github.com:josephmisiti/gord.git
cd gord
```

2. Install dependencies with uv:

```bash
uv sync
```

3. Set up your environment variables:

```bash
# Copy the example environment file
cp env.example .env

# Edit .env and add your API keys
# OPENAI_API_KEY=your-openai-api-key
# BRAVE_APIKEY=your-brave-api-key
```

### Usage

Run Gord in interactive mode:

```bash
uv run gord-agent
```

### Example Queries

Try asking Gord questions like:

- "Please create an underwriting report for 1428 west ave miami fl 33139?"
