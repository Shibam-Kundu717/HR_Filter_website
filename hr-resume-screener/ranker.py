def rank_candidate(required_skills: list, candidate_skills: list) -> dict:
    req_set = {s.strip().lower() for s in required_skills}
    cand_set = {s.strip().lower() for s in candidate_skills}

    matched = req_set.intersection(cand_set)
    extra = cand_set - req_set

    # 100% required skills match threshold
    is_qualified = len(matched) == len(req_set) if req_set else False

    # Priority Scoring: 70 base points + 5 pts per surplus skill (max 30 bonus)
    base_score = 70.0 if is_qualified else (len(matched) / len(req_set) * 50 if req_set else 0)
    surplus_bonus = min(len(extra) * 5, 30) if is_qualified else 0

    return {
        "is_qualified": is_qualified,
        "final_score": round(base_score + surplus_bonus, 2),
        "matched_skills": list(matched),
        "extra_skills": list(extra)
    }