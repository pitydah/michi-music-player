"""C6 isolated contract tests only; NOT the Michi repository integration suite."""

import unittest
from dataclasses import replace
from types import SimpleNamespace as NS  # noqa: N814

from michi.application.signal_truth_causal_view import (
    OutputAdoptionProof,
    RecorderContinuity,
    build_c6_qml_overlay,
    overlay_qml_stages,
    project_causal_family,
)


def family_event(family="dsd_pcm", state="running", eid="e1", device="dac"):
    return NS(family=family, state=state, execution_id=eid, device_id=device)


def dsp_event(
    state="effective",
    plan="dsp-7",
    revision=3,
    pipeline=13,
    host=9,
    runtime="native-A",
    readback=True,
):
    return NS(
        state=state,
        plan_id=plan,
        processing_generation=revision,
        pipeline_generation=pipeline,
        host_generation=host,
        runtime_identity=runtime,
        readback_proven=readback,
    )


def capture(family_events=(), dsp_events=(), revision=6):
    return NS(
        revision=revision,
        active=NS(identity="F03-active"),
        output_family_events=family_events,
        processing_events=dsp_events,
    )


def owner(family="dsd_pcm", state="running", eid="e1", device="dac"):
    return {
        "family": family,
        "state": state,
        "execution_id": eid,
        "stable_device_id": device,
        "generation": 4,
        "host_generation": 9,
        "binding_generation": 2,
    }


def f05(effective=True):
    return {
        "effective_state": "effective" if effective else "bypassed",
        "effective_plan_id": "dsp-7" if effective else None,
        "effective_revision": 3,
        "runtime_identity": "native-A",
        "readback_proven": effective,
    }


def adoption(family="dsd_pcm", eid="e1"):
    return OutputAdoptionProof(eid, family, 4, 2, 9, 13, "dsp-7", 3, "native-A", True)


def continuity(eid="e1"):
    return RecorderContinuity(3, 41, True, True, 6, eid)


class FamilyCausalTests(unittest.TestCase):
    def view(
        self,
        fe=None,
        de=None,
        ow=None,
        truth=None,
        proof=None,
        cont=None,
        delivery=None,
    ):
        return project_causal_family(
            capture=capture(
                (family_event(),) if fe is None else fe,
                (dsp_event(),) if de is None else de,
            ),
            owner=owner() if ow is None else ow,
            f05_truth=f05() if truth is None else truth,
            expected_execution_id="e1",
            adoption=proof,
            continuity=cont,
            delivery_claim=delivery,
        )

    def test_running_requires_owner_and_matching_event(self):
        self.assertEqual(self.view().family_state, "RUNNING_REPORTED")

    def test_no_f03_owner_link_denies_current_family(self):
        v = project_causal_family(
            capture=capture((family_event(),), (dsp_event(),)),
            owner=owner(),
            f05_truth=f05(),
            expected_execution_id=None,
            adoption=adoption(),
            continuity=continuity(),
        )
        self.assertEqual(v.family_state, "UNOBSERVED")
        self.assertNotEqual(v.dsp_state, "CURRENT_EXECUTION_CONFIRMED")

    def test_no_family_receipt_fails_closed(self):
        self.assertEqual(self.view(fe=()).family_state, "UNOBSERVED")

    def test_different_execution_cannot_be_inherited(self):
        self.assertEqual(
            self.view(fe=(family_event(eid="e0"),)).family_state, "UNOBSERVED"
        )

    def test_terminal_after_running_revokes(self):
        v = self.view(fe=(family_event(), family_event(state="unavailable")))
        self.assertEqual((v.family_state, v.dsp_state), ("TERMINATED", "UNOBSERVED"))

    def test_device_conflict(self):
        self.assertEqual(
            self.view(fe=(family_event(device="other"),)).family_state, "CONFLICTED"
        )

    def test_owner_ready_not_running(self):
        ow = owner()
        ow["state"] = "ready"
        self.assertEqual(self.view(ow=ow).family_state, "UNOBSERVED")

    def test_ready_event_not_claim_running(self):
        self.assertEqual(
            self.view(fe=(family_event(state="ready"),)).family_state, "READY_REPORTED"
        )

    def test_engine_effective_not_current_without_output_proof(self):
        self.assertEqual(self.view().dsp_state, "MOTOR_EFFECTIVE")

    def test_cross_execution_proof_rejected(self):
        v = self.view(proof=adoption(eid="other"), cont=continuity())
        self.assertEqual(v.dsp_state, "MOTOR_EFFECTIVE")
        self.assertIn("ST_C6_ADOPTION_SCOPE_MISMATCH", v.reasons)

    def test_proof_without_continuity_rejected(self):
        v = self.view(proof=adoption())
        self.assertEqual(v.dsp_state, "MOTOR_EFFECTIVE")
        self.assertIn("ST_C6_RECORDER_CONTINUITY_NOT_CERTIFIED", v.reasons)

    def test_wrong_epoch_revision_rejected(self):
        v = self.view(proof=adoption(), cont=replace(continuity(), capture_revision=7))
        self.assertEqual(v.dsp_state, "MOTOR_EFFECTIVE")

    def test_full_synthetic_proof_eligible(self):
        self.assertEqual(
            self.view(
                proof=adoption(), cont=continuity(), delivery="OBSERVED_RUNNING"
            ).dsp_state,
            "CURRENT_EXECUTION_CONFIRMED",
        )

    def test_output_delivery_missing_blocks_synthetic_confirmation(self):
        view = self.view(proof=adoption(), cont=continuity())
        self.assertEqual(view.dsp_state, "MOTOR_EFFECTIVE")
        self.assertIn("ST_C6_OUTPUT_DELIVERY_NOT_CERTIFIED", view.reasons)

    def test_output_delivery_terminal_blocks_synthetic_confirmation(self):
        view = self.view(
            proof=adoption(), cont=continuity(), delivery="OBSERVED_TERMINAL"
        )
        self.assertEqual(view.dsp_state, "MOTOR_EFFECTIVE")

    def test_scope_bad_binding_denied(self):
        self.assertEqual(
            self.view(
                proof=replace(adoption(), binding_generation=99), cont=continuity()
            ).dsp_state,
            "MOTOR_EFFECTIVE",
        )

    def test_f05_bypass_denied(self):
        self.assertEqual(self.view(truth=f05(False)).dsp_state, "UNOBSERVED")

    def test_latest_unscoped_terminal_revokes_effective(self):
        v = self.view(
            de=(dsp_event(), dsp_event(state="bypassed", plan=None, pipeline=None))
        )
        self.assertEqual(v.dsp_state, "UNOBSERVED")

    def test_scoped_terminal_revokes_effective(self):
        v = self.view(
            de=(dsp_event(), dsp_event(state="unavailable", plan=None, pipeline=13))
        )
        self.assertEqual(v.dsp_state, "UNOBSERVED")

    def test_other_pipeline_terminal_does_not_confer_current(self):
        v = self.view(
            de=(dsp_event(), dsp_event(state="unavailable", plan=None, pipeline=14))
        )
        self.assertEqual(v.dsp_state, "MOTOR_EFFECTIVE")
        self.assertNotEqual(v.dsp_state, "CURRENT_EXECUTION_CONFIRMED")

    def test_native_dsd_is_not_pcm_decode(self):
        v = self.view(fe=(family_event(family="native_dsd"),), ow=owner("native_dsd"))
        self.assertIn("no hay decodificación PCM", v.decode_override)
        self.assertEqual(v.dsp_state, "MOTOR_EFFECTIVE")  # motor only, not native route

    def test_dop_carrier_not_pcm_musical(self):
        v = self.view(fe=(family_event(family="dop"),), ow=owner("dop"))
        self.assertIn("no equivale a PCM musical", v.decode_override)
        self.assertIn("receptor no ha sido verificado", v.output_detail)

    def test_unknown_family_denied(self):
        v = self.view(ow=owner("x-unknown"))
        self.assertEqual(v.family_state, "UNOBSERVED")

    def test_cross_owner_overlay_stable_frame(self):
        cap = capture((family_event(),), (dsp_event(),))
        rec = NS(read_capture_state=lambda: cap)
        dto = {
            "status": "ACTIVE",
            "captureRevision": 6,
            "pathVerdict": "dsp",
            "reasonCodes": ["F03-PRESERVED"],
            "stages": [
                {"id": "source", "summary": "original"},
                {"id": "decode", "summary": "original"},
                {"id": "processing", "summary": "original"},
                {"id": "output", "summary": "original"},
                {"id": "device", "summary": "original"},
            ],
        }
        out = build_c6_qml_overlay(
            frame_payload=dto,
            recorder=rec,
            owner_scope_reader=lambda: owner(),
            f05_truth_reader=f05,
            linked_execution_reader=lambda _: "e1",
        )
        self.assertEqual(out["familyEvidenceState"], "RUNNING_REPORTED")
        self.assertEqual(out["pathVerdict"], "dsp")
        self.assertEqual(out["reasonCodes"], ["F03-PRESERVED"])
        self.assertEqual(dto["stages"][2]["summary"], "original")

    def test_cross_owner_overlay_capture_drift_refuses(self):
        caps = [
            capture((family_event(),), (dsp_event(),), 6),
            capture((family_event(),), (dsp_event(),), 7),
        ]
        rec = NS(read_capture_state=lambda: caps.pop(0))
        dto = {
            "status": "ACTIVE",
            "captureRevision": 6,
            "stages": [{"id": "output", "summary": "old"}],
        }
        out = build_c6_qml_overlay(
            frame_payload=dto,
            recorder=rec,
            owner_scope_reader=lambda: owner(),
            f05_truth_reader=f05,
            linked_execution_reader=lambda _: "e1",
        )
        self.assertEqual(out["familyEvidenceState"], "UNOBSERVED")
        self.assertEqual(out["stages"], dto["stages"])
        self.assertEqual(out["presentationWarning"], "ST_C6_CROSS_OWNER_READ_UNSTABLE")

    def test_owner_provider_failure_returns_safe_frame(self):
        cap = capture((family_event(),), (dsp_event(),))
        dto = {"status": "ACTIVE", "captureRevision": 6, "stages": [{"id": "output"}]}

        def fail():
            raise RuntimeError("provider down")

        out = build_c6_qml_overlay(
            frame_payload=dto,
            recorder=NS(read_capture_state=lambda: cap),
            owner_scope_reader=fail,
            f05_truth_reader=f05,
        )
        self.assertEqual(out["familyEvidenceState"], "UNOBSERVED")
        self.assertEqual(out["presentationWarning"], "ST_C6_OWNER_READ_FAILED")

    def test_historical_never_joins_current(self):
        dto = {
            "status": "HISTORICAL",
            "captureRevision": 6,
            "stages": [{"id": "output"}],
        }
        out = build_c6_qml_overlay(
            frame_payload=dto,
            recorder=None,
            owner_scope_reader=None,
            f05_truth_reader=None,
        )
        self.assertEqual(out["familyEvidenceState"], "UNOBSERVED")
        self.assertEqual(out["stages"], dto["stages"])

    def test_qml_overlay_preserves_node_order_and_data(self):
        orig = [
            {"id": "source", "summary": "FLAC", "reasonCodes": ["canonical"]},
            {"id": "decode", "summary": "PCM", "reasonCodes": ["canonical2"]},
            {"id": "processing", "summary": "X"},
            {"id": "output", "summary": "Y"},
            {"id": "device", "summary": "Z"},
        ]
        v = self.view(fe=(family_event(family="native_dsd"),), ow=owner("native_dsd"))
        updated = overlay_qml_stages(orig, v)
        self.assertEqual([x["id"] for x in updated], [x["id"] for x in orig])
        self.assertEqual(updated[0]["reasonCodes"], ["canonical"])
        self.assertEqual(updated[1]["reasonCodes"], ["canonical2"])
        self.assertEqual(orig[1]["summary"], "PCM")
        self.assertEqual(updated[1]["state"], "unknown")


if __name__ == "__main__":
    unittest.main()
