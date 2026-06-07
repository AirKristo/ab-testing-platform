# CUPED Implementation Notes

## What is CUPED?

CUPED (Controlled-experiment Using Pre-Experiment Data) is a variance reduction
technique developed at Microsoft (Deng et al., 2013) and later adopted by Meta,
Netflix, and other major experimentation platforms.

The core insight: in any A/B test, the variance in our outcome metric Y comes
from two sources:
1. **User-level baseline variation** — some users naturally spend more than others
2. **Treatment effect variation** — the actual difference caused by the experiment

If we can "subtract out" source #1 using pre-experiment data, we get a more
precise estimate of the treatment effect — equivalent to running the experiment
with a much larger sample size.

## The Math

Let:
- Y = outcome metric for each user (e.g., revenue during experiment)
- X = pre-experiment covariate (e.g., historical spend before assignment)

The CUPED-adjusted outcome is:

    Y_cuped = Y - θ * (X - mean(X))

where θ is the regression coefficient of Y on X:

    θ = cov(X, Y) / var(X)

**Why this works:**
- We're regressing out the linear relationship between Y and X
- The residual (Y_cuped) has less variance than Y when X and Y are correlated
- Specifically: var(Y_cuped) = var(Y) * (1 - ρ²)
  where ρ is the correlation between X and Y

**Example:** If correlation is 0.5, variance reduction is 25% (1 - 0.25). This
is equivalent to running the experiment with 33% more sample size — significant
savings.

## Key Implementation Decisions

### 1. The covariate must be PRE-experiment

The covariate must be measured BEFORE the user was assigned to the experiment.
If we used post-assignment data, we'd contaminate the covariate with treatment
effects, biasing the estimate.

**Our approach:** Each Assignment has an `assigned_at` timestamp. We compute the
covariate by querying orders with `created_at < assigned_at`. This gives us a
clean snapshot of pre-experiment behavior.

### 2. θ is computed from POOLED data

We compute θ using all variants combined (not separately per variant). If we
computed θ separately for each variant, we'd be using outcome data to choose
the adjustment — a form of data snooping that biases the result.

This is sometimes called "regression adjustment with a global slope."

### 3. CUPED preserves unbiasedness

The mean of Y_cuped within each variant equals the mean of Y (in expectation).
This means CUPED doesn't change WHAT we're estimating, only how PRECISELY we
estimate it. The point estimate of the treatment effect is the same; the
confidence interval just gets tighter.

## Connection to Causal Inference

CUPED is essentially **regression adjustment with a single pre-treatment
covariate**. It's a special case of techniques like:

- ANCOVA (Analysis of Covariance)
- Difference-in-Differences with pre-period data
- More generally, controlling for confounders that predict the outcome

The key difference from typical regression: in CUPED we use the covariate to
reduce variance, not to control for confounding (random assignment already
handles confounding).

## What Covariate to Choose

A good CUPED covariate should:
1. Be **measured before the experiment** (no contamination)
2. Be **correlated with the outcome** (higher correlation → more variance reduction)
3. Be **observable for all users** (or at least most)

For our e-commerce platform:
- Historical spend → strongly correlated with future spend (revenue_per_user metric)
- Order count → correlated with conversion rate
- Days since signup → weak correlation, less useful

We default to `historical_spend` since it correlates with most outcomes.

## Limitations & When NOT to Use CUPED

- **First-time users:** They have no pre-experiment data, so CUPED can't help them.
  We treat their covariate as 0 (or impute the population mean).
- **Low correlation:** If correlation is near 0, CUPED provides no benefit. The
  adjustment is mathematically valid but unnecessary.
- **New metrics:** If the experiment is the FIRST time a user sees a new feature,
  there's no historical equivalent to use as a covariate.

## References

- Deng, Xu, Kohavi, Walker (2013). "Improving the Sensitivity of Online Controlled
  Experiments by Utilizing Pre-Experiment Data."
- Microsoft ExP Platform: [aka.ms/exp](https://aka.ms/exp)
- Meta's overview: [research.facebook.com](https://research.facebook.com)