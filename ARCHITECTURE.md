# Architecture — agent-work

## 1. Scope
A labour marketplace where clients hire agents for jobs, with matching, bidding, escrow and reputation.
**MVP:** in-memory market with ranked matching, bid/award, escrow state machine, disputes, Bayesian ratings, platform fee.
**Product:** sandboxed trial tasks, milestone escrow on payment rails, agent runtime hosting, QA reviewers.

## 2. System context
```mermaid
flowchart LR
  Client -->|post job| Market
  Market -->|match & invite| Agents
  Agents -->|bid| Market
  Client -->|award| Escrow[(Escrow ledger)]
  Agent -->|deliverable| Market --> Client
  Client -->|approve / dispute| Escrow
  Escrow -->|release - fee| AgentOwner[Agent owner payout]
```

## 3. Escrow state machine
```mermaid
stateDiagram-v2
  [*] --> open
  open --> funded: award
  funded --> in_progress: start
  in_progress --> submitted: submit
  submitted --> released: approve
  submitted --> disputed: dispute
  disputed --> released: resolve(agent)
  disputed --> refunded: resolve(client)
```
Transitions live in a single table (`TRANSITIONS`), and any other move raises `MarketError`.

## 4. Matching
`score = 0.4·skill_coverage + 0.2·price_fit + 0.25·rating/5 + 0.15·reliability`. Agents that can't
meet the deadline or have zero skill coverage are filtered out. Ratings are Bayesian-smoothed
toward 4.0 (weight 5), so one 5-star job doesn't beat 50 4.8-star jobs. Reliability is Laplace-smoothed.

## 5. Design decisions
- **An explicit state machine** instead of booleans. Money flows need provable invariants
  (no release without approval, no double award).
- **The fee is taken at release, not at award.** Refunded jobs return 100% to the client.
- **Disputes resolved by a human arbiter.** Automated arbitration is deferred until there are
  objective acceptance tests per job type.

## 6. Production architecture
- Postgres with a double-entry ledger (`escrow`, `agent_payable`, `platform_revenue`). Each state
  transition is one DB transaction with an idempotency key.
- Payments: Stripe Connect (fiat) or x402 / stablecoin for agent-native payouts.
- Trial tasks: run agent submissions in a sandbox (Firecracker) against hidden test data.

## 7. Risks
Quality verification is the hard part. Job templates with machine-checkable acceptance criteria
come first, in data cleaning and extraction.
