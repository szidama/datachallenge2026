"""Régression quantile directe des variations d'inscriptions sur l'horizon amorti."""
from statistics import mean

QUANTILES = {"bas": .2, "central": .5, "haut": .8}
DAMPING = {"quantile80": .8, "quantile95": .95}
HORIZONS = (1, 2)


def steps(horizon, phi):
    return (1 - phi**horizon) / (1 - phi)


def loss(residual, tau):
    return max(tau * residual, (tau - 1) * residual)


def fit(series, phi):
    """Le minimum de la perte pinball sans constante est un quantile pondéré de Δy/x."""
    by_year = dict(series)
    examples = []
    origins = set()
    for year, level in series:
        for h in HORIZONS:
            if year + h in by_year:
                x = steps(h, phi)
                examples.append(((by_year[year+h] - level) / x, x))
                origins.add(year)
    if len(origins) < 3:
        return None
    examples.sort()
    weight = sum(x for _, x in examples)
    slopes = {}
    for scenario, tau in QUANTILES.items():
        cumulative = 0.
        for slope, x in examples:
            cumulative += x
            if cumulative >= tau * weight:
                slopes[scenario] = slope
                break
    return dict(slopes=slopes, examples=len(examples), origins=len(origins))


def predict(level, horizon, fitted, phi):
    x = steps(horizon, phi)
    return {k: level + x*b for k, b in fitted["slopes"].items()}


def evaluate(series, requested):
    """Les trois quantiles d'un pli sont toujours ajustés avant l'année cible."""
    by_year = dict(series)
    scores = []
    losses = {}
    for model, phi in DAMPING.items():
        folds = {h: [] for h in HORIZONS}
        for stop in range(4, len(series)):
            train = series[:stop]
            origin, level = train[-1]
            fitted = fit(train, phi)
            if fitted is None:
                continue
            for h in HORIZONS:
                if origin+h not in by_year:
                    continue
                actual = by_year[origin+h]
                estimates = predict(level, h, fitted, phi)
                errors = {k: max(0, round(v)) - actual for k, v in estimates.items()}
                score = mean(loss(-errors[k], tau) for k, tau in QUANTILES.items())
                folds[h].append((errors["central"], score))
        combined = [v for pairs in folds.values() for _, v in pairs]
        losses[model] = mean(combined) if combined else None
        for h, pairs in folds.items():
            scores.append(dict(model=model, horizon=h, n=len(pairs),
                               mae=round(mean(abs(e) for e, _ in pairs), 2) if pairs else None,
                               bias=round(mean(e for e, _ in pairs), 2) if pairs else None,
                               pinball=round(mean(v for _, v in pairs), 2) if pairs else None))
    selected = requested
    if requested == "ml_auto":
        # En cas d'égalité ou en l'absence de test, l'amortissement le plus fort prime.
        selected = min(DAMPING, key=lambda k: float("inf") if losses[k] is None else losses[k])
    phi = DAMPING[selected]
    fitted = fit(series, phi)
    diagnostics = dict(quantiles=QUANTILES, phi=phi, observations=len(series), fitted=fitted,
                       base_level=series[-1][1] if series else None,
                       selection_scores=losses, requested=requested, training_horizons=list(HORIZONS),
                       fit_formula="βτ minimise Σ ρτ[(y(t+h) − y(t)) − βτ x(h)], avec ρτ(u) = max(τu, (τ−1)u).",
                       forecast_formula="x(h) = (1 − φʰ)/(1 − φ). Projection = max(0, arrondi[y(T) + βτ x(h)]).",
                       selection_rule="Perte quantile moyenne sur les trois trajectoires et tous les tests à un ou deux ans. En sélection automatique, le score minimal prime, puis φ = 0,80 en cas d’égalité.")
    return selected, scores, diagnostics
