"""
Similar-course recommendations based on course titles + descriptions.

How it works (TF-IDF + cosine similarity):
  1. Each course becomes a "document": its title (repeated TITLE_WEIGHT times)
     plus its catalog description.
  2. TfidfVectorizer turns every document into a vector of word weights.
     Words that are rare across the catalog ("kanji", "actuarial") get high
     weight; words that appear everywhere ("students", "course") get low weight.
  3. Cosine similarity between two vectors = how much vocabulary two courses
     share, weighted by how distinctive that vocabulary is. 0 = nothing in
     common, 1 = identical text.
  4. We keep the top N matches per course after filtering out junk
     (cross-listed duplicates, generic placeholder courses, grad/undergrad mix).

This runs OFFLINE via `python manage.py build_similar_courses`, never during
a page request. The course detail page only reads the saved results.

Every knob worth tuning lives in DEFAULT_SETTINGS below. Try changes with:
    python manage.py build_similar_courses --preview "COMPSCI 351" --set title_weight=3
"""

import re
import time
import unicodedata

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer


DEFAULT_SETTINGS = {
    # --- What gets saved ---------------------------------------------------
    # How many similar courses to store per course (template shows the first 4).
    "top_n": 6,
    # Matches scoring below this are dropped. Raise it if weak/irrelevant
    # matches show up; lower it if too many courses end up with no matches.
    "min_score": 0.12,

    # --- How text becomes vectors -----------------------------------------
    # Descriptions are short (median ~20 words), so the title matters a lot.
    # Repeating it makes title words count more. 1 = no extra weight.
    "title_weight": 2,
    # (1, 1) = single words only. (1, 2) also uses two-word phrases like
    # "data structures", which helps tell "data structures" from "data analysis".
    "ngram_range": (1, 2),
    # Ignore words that appear in fewer than this many courses (typos, one-offs).
    "min_df": 2,
    # Ignore words that appear in more than this fraction of courses.
    "max_df": 0.5,
    # Dampens repeated words (log scaling). Usually best left True.
    "sublinear_tf": True,
    # Catalog boilerplate that says nothing about the subject. Added on top of
    # scikit-learn's standard English stop words. Add to this list when you see
    # matches that only share generic words.
    "extra_stop_words": [
        "course", "courses", "student", "students", "study", "studies",
        "introduction", "introductory", "advanced", "topics", "topic",
        "including", "emphasis", "focus", "focuses", "issues", "examination",
        "selected", "various", "related", "special", "seminar", "credit",
        "credits", "prerequisite", "prereq", "consent", "instructor",
        "offered", "semester", "class", "classes", "skills", "understanding",
        "overview", "survey", "principles", "concepts", "basic", "fundamentals",
    ],

    # --- Filters ------------------------------------------------------------
    # Only recommend undergrad courses on undergrad pages and grad on grad.
    "same_tier_only": True,
    # Course numbers at or above this are treated as graduate level.
    "grad_level_start": 700,
    # Anything this similar is assumed to be a cross-listing of the same course
    # (e.g. COMPSCI 351 / COMPST 751, PSYCH 101 / PSYCH 101X) and is skipped.
    "duplicate_score": 0.95,
    # Added to the score when both courses are in the same department.
    # 0 = department doesn't matter. Try 0.05 to keep results closer to home.
    "same_department_boost": 0.0,
    # Placeholder courses with these titles get no recommendations and are
    # never recommended (lowercase, trailing ":" ignored).
    "skip_titles": [
        "candidate for degree", "first-year seminar", "honors seminar",
        "independent study", "independent reading", "thesis", "dissertation",
        "master's thesis", "internship", "directed study", "directed research",
    ],
    # Same idea, matched against the description text.
    "skip_description_phrases": [
        "topics are announced in the schedule of classes",
        "minimum credit load requirement",
    ],
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def normalize_text(text):
    """Fix catalog quirks: ligatures like 'ﬁ' -> 'fi', non-breaking spaces, case."""
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", " ", text).strip().lower()


def normalize_code(code):
    """'ATM\\xa0SCI 464' and 'atm sci 464' both become 'ATM SCI 464'."""
    return normalize_text(code).upper()


def split_code(code):
    """'COMPSCI 351' -> ('COMPSCI', 351, '351'); 'PSYCH 101X' -> ('PSYCH', 101, '101')."""
    code = normalize_code(code)
    match = re.match(r"^(.*?)\s*(\d+)\w*$", code)
    if not match:
        return code, None, None
    department, digits = match.group(1).strip(), match.group(2)
    return department, int(digits), digits


def is_placeholder(title, description, settings):
    clean_title = normalize_text(title).rstrip(":").strip()
    if clean_title in settings["skip_titles"]:
        return True
    clean_description = normalize_text(description)
    return any(phrase in clean_description for phrase in settings["skip_description_phrases"])


def is_grad(number, settings):
    return number is not None and number >= settings["grad_level_start"]


# ---------------------------------------------------------------------------
# Main computation
# ---------------------------------------------------------------------------

def compute_similar_courses(courses, overrides=None, chunk_size=1000):
    """
    courses: list of (id, code, title, description) tuples.
    overrides: dict of DEFAULT_SETTINGS keys to change for this run.

    Returns (results, stats) where results maps
    course_id -> [(similar_course_id, score), ...] best first.
    """
    settings = {**DEFAULT_SETTINGS, **(overrides or {})}
    started = time.perf_counter()

    # Leave placeholder courses out entirely.
    usable = [c for c in courses if not is_placeholder(c[2], c[3], settings)]
    ids = np.array([c[0] for c in usable])
    titles = [normalize_text(c[2]).rstrip(":").strip() for c in usable]
    parts = [split_code(c[1]) for c in usable]
    departments = np.array([p[0] for p in parts])
    base_codes = np.array([f"{p[0]} {p[2]}" for p in parts])
    grad = np.array([is_grad(p[1], settings) for p in parts])

    documents = [
        " ".join([normalize_text(c[2])] * settings["title_weight"]) + " " + normalize_text(c[3])
        for c in usable
    ]
    vectorizer = TfidfVectorizer(
        stop_words=list(ENGLISH_STOP_WORDS.union(settings["extra_stop_words"])),
        ngram_range=tuple(settings["ngram_range"]),
        min_df=settings["min_df"],
        max_df=settings["max_df"],
        sublinear_tf=settings["sublinear_tf"],
        dtype=np.float32,
    )
    matrix = vectorizer.fit_transform(documents)  # rows are L2-normalized
    vectorized_at = time.perf_counter()

    results = {}
    top_n = settings["top_n"]
    # Process rows in chunks so memory stays around chunk_size x n_courses floats
    # (~28 MB for 1000 x 7000) instead of the full n x n matrix.
    for start in range(0, matrix.shape[0], chunk_size):
        stop = min(start + chunk_size, matrix.shape[0])
        scores = (matrix[start:stop] @ matrix.T).toarray()

        if settings["same_department_boost"]:
            same_dept = departments[start:stop, None] == departments[None, :]
            scores += same_dept * settings["same_department_boost"]

        for offset, row in enumerate(scores):
            i = start + offset
            row[i] = -1  # never recommend a course to itself
            if settings["same_tier_only"]:
                row[grad != grad[i]] = -1

            # Grab a few extra candidates because some get filtered below.
            candidate_count = min(top_n * 4, len(row) - 1)
            candidates = np.argpartition(-row, candidate_count)[:candidate_count]
            candidates = candidates[np.argsort(-row[candidates])]

            picked, seen_titles = [], {titles[i]}
            for j in candidates:
                score = float(row[j])
                if score < settings["min_score"]:
                    break  # sorted, so everything after is lower
                if score >= settings["duplicate_score"]:
                    continue  # cross-listed copy of the same course
                if base_codes[j] == base_codes[i] or titles[j] in seen_titles:
                    continue  # PSYCH 101X vs 101, or same course under another dept
                seen_titles.add(titles[j])
                picked.append((int(ids[j]), round(min(score, 1.0), 4)))
                if len(picked) == top_n:
                    break
            if picked:
                results[int(ids[i])] = picked

    finished = time.perf_counter()
    stats = {
        "courses_total": len(courses),
        "courses_used": len(usable),
        "courses_with_matches": len(results),
        "vocabulary_size": len(vectorizer.vocabulary_),
        "vectorize_seconds": round(vectorized_at - started, 2),
        "similarity_seconds": round(finished - vectorized_at, 2),
        "total_seconds": round(finished - started, 2),
    }
    return results, stats
