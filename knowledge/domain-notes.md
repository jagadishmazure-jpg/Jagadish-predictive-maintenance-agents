# Domain notes: predictive maintenance operations

Distilled from reliability-engineering practice, in own words.

## Why plants lose money to maintenance
Unplanned downtime costs orders of magnitude more than planned work: lost
production, rush parts, overtime, and sometimes safety exposure. The classic
failure is the "run-to-failure by default" plant — no trending, so every
failure is a surprise.

## Condition monitoring in one paragraph
Rotating equipment talks before it fails. Vibration rises as bearings wear;
temperature follows friction. Trending both over days-to-weeks separates a
real degradation (steady slope) from noise (flat with scatter). A single
threshold catches emergencies; the slope predicts them.

## Remaining useful life (RUL)
RUL is an estimate with a confidence story, not a prophecy. A transparent
feature breakdown (which sensor, which slope, how much weight) is what makes
a prediction actionable — a planner can check the sensor before ordering
parts. Opaque scores get ignored.

## Work-order prioritization
Backlogs are always longer than the available window. The ranking that
works in practice multiplies three things: how critical the asset is, how
likely it is to fail soon, and what production loses if it does. Anything
else (first-in-first-out, loudest requester) misallocates the window.

## The human stays in the loop
Line stops and emergency work are money-and-safety decisions. The agent
recommends, ranks, and cites — a human approves. That boundary is the whole
point of the confirmation gates in this repo.
