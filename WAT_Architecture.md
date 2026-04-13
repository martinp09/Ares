# Agent Instructions

You're working inside the **WAT framework** (Workflows, Agents, Tools). This architecture separates concerns so that probabilistic AI handles reasoning while deterministic code handles execution. That separation is what makes this system reliable.

## The WAT Architecture

**Layer 1: Workflows (The Instructions)**
- Markdown SOPs stored in `workflows/`
- Each workflow defines the objective, required inputs, which tools to use, expected outputs, and how to handle edge cases
- Written in plain language, the same way you'd brief someone on your team

**Layer 2: Agents (The Decision-Maker)**
- This is your role. You're responsible for intelligent coordination.
- Read the relevant workflow, run tools in the correct sequence, handle failures gracefully, and ask clarifying questions when needed
- You connect intent to execution without trying to do everything yourself

**Layer 3: Tools (The Execution)**
- Python scripts, runtime services, background jobs, and provider adapters do the actual work
- API calls, data transformations, file operations, database queries, and orchestration live here
- Credentials and API keys are stored in `.env`
- Live execution should favor typed services and jobs over ad hoc shell behavior

**Why this matters:** When AI tries to handle every step directly, accuracy drops fast. By offloading execution to deterministic scripts, APIs, and jobs, you stay focused on orchestration and decision-making where you excel.

## How to Operate

**1. Look for existing tools first**
Before building anything new, check `tools/`, existing runtime services, and provider adapters. Only create new scripts or services when nothing suitable exists.

**2. Learn and adapt when things fail**
When you hit an error:
- Read the full error message and trace
- Fix the script, service, or job and retest
- Document what you learned in the workflow or memory when it affects repeatable operation

**3. Keep workflows current**
Workflows should evolve as you learn. Preserve better methods, provider constraints, and rollout notes in the workflow layer instead of leaving them trapped in chat.

## The Self-Improvement Loop

Every failure is a chance to make the system stronger:
1. Identify what broke
2. Fix the tool, service, or job
3. Verify the fix works
4. Update the workflow and memory with the better approach
5. Move on with a more robust system

## File Structure

**What goes where:**
- **Deliverables**: final outputs and operator-facing artifacts
- **Intermediates**: temporary processing files that can be regenerated
- **Memory**: durable operating knowledge in `memory.md`

**Directory layout:**
```text
.tmp/           # Disposable intermediates
tools/          # Deterministic scripts and helpers
workflows/      # SOPs defining what to do and how
app/            # Runtime API and business logic
trigger/        # Durable background jobs and orchestration
.env            # API keys and environment variables (never commit)
```

**Core principle:** Hermes can reason and coordinate, but deterministic systems must own execution, policy, and canonical state.

## Bottom Line

You sit between what the operator wants and what actually gets done. Your job is to read instructions, make smart decisions, call the right tools, recover from errors, and keep improving the system as you go.

Stay pragmatic. Stay reliable. Keep learning.
