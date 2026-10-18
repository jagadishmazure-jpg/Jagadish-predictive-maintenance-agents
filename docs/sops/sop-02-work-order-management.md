# SOP-02: Work-Order Management

## Raising work orders
Any predicted failure with remaining useful life under 30 days gets a work
order within one shift. The work-order prioritizer ranks the backlog by
criticality x failure probability x production impact; P1 items start
before the next planned window.

## Gated actions
Emergency work orders (unplanned, safety-adjacent) require a named approver
in the confirmation gate. Line-stop recommendations are always T4 and gated:
no line stops without a human decision recorded in the audit chain.

## Closure
Close a work order only after a post-maintenance reading confirms the trend
has reset. Re-baseline the asset's sensor history on closure.
