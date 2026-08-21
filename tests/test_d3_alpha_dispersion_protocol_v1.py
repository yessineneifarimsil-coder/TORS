from pathlib import Path
import json
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "config" / "d3_alpha_dispersion_protocol_v1.json"


def _protocol():
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_d3_protocol_frozen_world_ensemble_and_firewalls():
    p = _protocol()
    d = p["design_ensemble"]

    assert p["status"] == "prospectively synchronized; no D3 technology world observed"
    assert p["production_generator"]["candidate_id"] == "d29_kernel"
    assert p["production_generator"]["frozen"] is True

    assert d["master_seed_namespace"] == 74001
    assert d["child_generation"] == "numpy.random.SeedSequence.spawn"
    assert d["total_worlds_frozen"] == 400
    assert d["initial_worlds"] == 200
    assert len(d["world_seeds"]) == 400
    assert len(set(d["world_seeds"])) == 400
    assert d["contexts_per_world"] == 1000
    assert d["alternatives_per_context"] == 6
    assert d["observations_per_criterion_per_world"] == 6000
    assert d["rho"] == 0.4
    assert d["sigma_x"] == 0.0
    assert d["external_test_used"] is False
    assert d["primary_seeds_used"] is False
    assert d["structural_validation_seeds_used"] is False
    assert d["protected_seed_collision_count"] == 0


def test_d3_estimand_and_convergence_are_frozen():
    p = _protocol()
    e = p["dispersion_estimand"]
    c = p["convergence"]

    assert e["q_transform"] == "log(1+2g)/log(3)"
    assert e["within_world_statistic"] == "mean absolute deviation from within-world mean q"
    assert e["context_aggregation_before_qMAD"] is False
    assert e["criterion_minmax_before_qMAD"] is False
    assert e["superpopulation_summary"] == "arithmetic mean of world-specific q-MAD"

    assert c["initial_checkpoints"] == [50,100,150,200]
    assert c["initial_order_compare"] == [150,200]
    assert c["relative_95pct_half_width_target"] == 0.05
    assert c["expanded_checkpoints"] == [250,300,350,400]
    assert c["expanded_order_compare"] == [350,400]
    assert c["expanded_final_W"] == 400


def test_operational_configs_are_synchronized_but_historical_72001_is_preserved():
    b = yaml.safe_load((ROOT / "config" / "benchmark.yaml").read_text(encoding="utf-8"))
    s = yaml.safe_load((ROOT / "config" / "seeds.yaml").read_text(encoding="utf-8"))

    a = b["alpha_stress_test"]
    assert a["assignment_source"]["type"] == "superpopulation_anchored_technology_world_ensemble"
    assert a["assignment_source"]["master_seed_namespace"] == 74001
    assert a["assignment_source"]["initial_worlds"] == 200
    assert a["assignment_source"]["total_child_worlds"] == 400
    assert a["dispersion_measure"]["statistic"] == "mean_absolute_deviation_from_mean"
    assert a["dispersion_measure"]["preprocessing"] == "none"
    assert a["dispersion_measure"]["superpopulation_aggregation"] == "arithmetic_mean_across_worlds"

    assert s["alpha_stress_design_pool"]["master_seed"] == 72001
    assert s["d3_alpha_dispersion_superpopulation"]["master_seed_namespace"] == 74001
    assert s["d3_alpha_dispersion_superpopulation"]["total_child_worlds"] == 400
    assert s["d3_alpha_dispersion_superpopulation"]["initial_worlds"] == 200
