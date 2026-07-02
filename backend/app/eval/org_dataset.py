"""Organization-idiosyncratic ticket dataset — the "Northwind conventions".

The killer question for any memory agent is: *"wouldn't a frontier model ace this
zero-shot, no memory needed?"* On generic tickets — yes. So this dataset makes ground
truth depend on ORGANIZATION CONVENTIONS that no model can know a priori, only learn
from experience:

  * "Project Falcon" tickets   → technical (Falcon is the white-glove self-hosted product;
                                            its integration team owns EVERY Falcon ticket,
                                            invoices and user-adds included)
  * refund requests            → account   (company policy: refunds via account managers,
                                            NOT billing, however billing-flavoured they read)
  * Acme + sync issues         → shipping  (known bug in Acme's shipping-provider feed;
                                            reads like a technical ticket, isn't)
  * beta-build reports         → feedback  (beta reports route to the product team)
  * purchase-order questions   → billing   (PO desk lives in billing, even "where is my
                                            delivery" phrasing)

Each convention ticket is written so its SURFACE reading points at the wrong category.
Zero-shot models score high on the plain subset and fail the convention subset; an agent
that accumulates org experience closes that gap. That is the claim Experiment 2 tests.

Design note: the five conventions map to five DISTINCT truth categories, so no category
becomes the majority class and filler noise can't spuriously correlate with one truth.

Deterministic and seeded, like everything else in the eval suite.
"""
from __future__ import annotations

import random

from .dataset import TEMPLATES, _paraphrase

# (marker-for-filtering, true category, templates whose surface reading points elsewhere)
CONVENTIONS: list[tuple[str, str, list[str]]] = [
    ("falcon", "technical", [
        "We were invoiced twice for the Project Falcon subscription.",
        "Need a pricing breakdown for the Project Falcon add-on seats.",
        "Please add two admin users to our Project Falcon workspace.",
        "The hardware kit for our Project Falcon pilot hasn't arrived, tracking is stuck.",
    ]),
    ("refund", "account", [
        "I want a refund for last month's charge, it doesn't match my plan.",
        "Please process a refund for the duplicate payment on my invoice.",
        "Requesting a refund — I was billed again after cancelling.",
        "Can I get a refund on the annual renewal that just went through?",
    ]),
    ("acme", "shipping", [
        "Acme here — sync between the app and our warehouse feed is broken again.",
        "Our Acme account isn't syncing orders since yesterday's update.",
        "Acme: data sync stalls halfway and never completes.",
        "The Acme integration sync throws timeout errors all morning.",
    ]),
    ("beta", "feedback", [
        "Found a crash in the beta build when exporting reports.",
        "The new beta dashboard breaks on mobile, thought you should know.",
        "Beta build 2.3 keeps logging me out mid-session.",
        "In the beta, the search bar returns no results half the time.",
    ]),
    ("purchase", "billing", [
        "When will the items on our purchase order arrive at the depot?",
        "Our purchase order shipment shows the wrong delivery address.",
        "Tracking hasn't updated for the purchase order we placed last week.",
        "The purchase order delivery came damaged, we need replacements.",
    ]),
]

_MARKERS = [m for m, _, _ in CONVENTIONS]

# Plain pool: the generic templates, minus any that collide with a convention marker
# (e.g. the stock billing templates that mention refunds — those now belong to the
# refund convention and must not appear with a contradicting label).
PLAIN: dict[str, list[str]] = {
    cat: [t for t in temps if not any(m in t.lower() for m in _MARKERS)]
    for cat, temps in TEMPLATES.items()
}


def make_org_sessions(
    n_sessions: int = 4, per_session: int = 12, seed: int = 11
) -> list[list[tuple[str, str, bool]]]:
    """Sessions of (ticket_text, true_category, is_convention).

    Half of each session is convention tickets (markers round-robin so every
    convention recurs early — learnable by session 2), half plain tickets.
    """
    rng = random.Random(seed)
    conv_cycle = 0
    sessions: list[list[tuple[str, str, bool]]] = []
    for _ in range(n_sessions):
        session: list[tuple[str, str, bool]] = []
        n_conv = per_session // 2
        for _ in range(n_conv):
            _, truth, temps = CONVENTIONS[conv_cycle % len(CONVENTIONS)]
            conv_cycle += 1
            session.append((_paraphrase(rng, rng.choice(temps)), truth, True))
        for _ in range(per_session - n_conv):
            cat = rng.choice(list(PLAIN.keys()))
            session.append((_paraphrase(rng, rng.choice(PLAIN[cat])), cat, False))
        rng.shuffle(session)
        sessions.append(session)
    return sessions
