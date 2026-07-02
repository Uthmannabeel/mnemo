"""Deterministic synthetic support-ticket dataset.

Each category has characteristic phrasings. There IS a learnable signal (keywords
correlate with category) but with enough surface variation that a memoryless agent
cannot ace it cold — exactly the setup where accumulated memory should win.

Seeded, so the accuracy curve is reproducible for the demo and CI.
"""
from __future__ import annotations

import random

TEMPLATES: dict[str, list[str]] = {
    "billing": [
        "I was charged twice for my subscription this month, please refund the duplicate.",
        "My invoice shows a charge I don't recognize — can you explain this billing line?",
        "Why did my monthly payment go up? I want a breakdown of the new pricing.",
        "I cancelled last week but was still charged for a renewal today.",
        "Requesting a refund for the duplicate charge on my credit card.",
    ],
    "technical": [
        "The app crashes every time I try to upload a file, error code 500.",
        "I can't log in — the page just spins and never loads the dashboard.",
        "Sync is broken between my phone and laptop, changes don't propagate.",
        "Getting a 'connection timed out' error whenever I open the reports tab.",
        "The export button does nothing when I click it, seems like a bug.",
    ],
    "account": [
        "I need to reset my password but the reset email never arrives.",
        "Please help me change the email address associated with my account.",
        "I want to delete my account and remove all my personal data.",
        "How do I add a teammate as an admin to our workspace account?",
        "My account got locked after too many login attempts, please unlock it.",
    ],
    "shipping": [
        "My package was supposed to arrive yesterday but the tracking hasn't updated.",
        "The order shipped to the wrong address, how do I redirect the delivery?",
        "I received a damaged item in my shipment, need a replacement sent.",
        "Where is my order? The courier tracking says pending for five days.",
        "Can I upgrade to express shipping for the order I just placed?",
    ],
    "feedback": [
        "Just wanted to say the new dark mode looks fantastic, great work team!",
        "A suggestion: it would be great to have keyboard shortcuts for navigation.",
        "I love the product but wish the mobile app had offline support.",
        "Feedback: the onboarding tutorial was really clear and helpful, thank you.",
        "Feature request — please add CSV import to the dashboard.",
    ],
}

CATEGORIES = list(TEMPLATES.keys())


# Shared, category-neutral filler. Real tickets are padded with chit-chat and
# context that is NOT discriminative. Sprinkling it in pollutes raw cosine
# similarity (episodes look alike) without changing the true category — so a
# k-NN-over-raw-episodes baseline degrades, while a distilled keyword rule that
# keys on the ONE discriminative token stays robust. This is the realistic setting.
_FILLER = [
    "I've been a customer for three years now and generally really enjoy the service.",
    "Sorry to bother you, I know your team is busy and doing great work.",
    "I tried searching the help center first but couldn't find a clear answer.",
    "This is my second time reaching out about something this month.",
    "For context, I'm on the annual plan and use the product daily for work.",
    "Not sure if this is the right channel but figured I'd ask anyway.",
    "My colleague suggested I contact support directly about this.",
    "Hoping we can sort this out quickly as it's a bit time sensitive.",
]


def _paraphrase(rng: random.Random, base: str) -> str:
    """Surface variation + neutral filler noise so raw k-NN can't trivially win."""
    prefixes = ["", "Hi, ", "Hello team, ", "Quick one — ", "Urgent: ", "FYI, "]
    suffixes = ["", " Thanks.", " Appreciate the help.", " Please advise.", " -- a frustrated user"]
    parts = [rng.choice(prefixes) + base + rng.choice(suffixes)]
    # Insert 1-2 filler sentences around the real content.
    for filler in rng.sample(_FILLER, rng.randint(1, 2)):
        parts.insert(rng.randint(0, len(parts)), filler)
    return " ".join(parts)


def make_sessions(
    n_sessions: int = 8, per_session: int = 20, seed: int = 7
) -> list[list[tuple[str, str]]]:
    """Return sessions; each is a list of (ticket_text, true_category)."""
    rng = random.Random(seed)
    sessions: list[list[tuple[str, str]]] = []
    for _ in range(n_sessions):
        session: list[tuple[str, str]] = []
        for _ in range(per_session):
            cat = rng.choice(CATEGORIES)
            base = rng.choice(TEMPLATES[cat])
            session.append((_paraphrase(rng, base), cat))
        sessions.append(session)
    return sessions
