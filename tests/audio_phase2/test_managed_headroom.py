"""AP2-F06 — explicit headroom policy (no silent level changes).

The required boost is a pure policy input; the compensation is ONE visible
preamp node whose attenuation equals the worst-case positive boost.
"""

from __future__ import annotations

from michi.application.managed_pcm_output_planner import (
    AUTO_HEADROOM_NODE_ID,
    required_headroom_db,
    with_auto_headroom,
)
from michi.domain.audio_processing import (
    BiquadType,
    GraphicEqLayout,
    GraphicEqNode,
    ParametricEqNode,
    PeqBand,
    PreampNode,
    ProcessingGraph,
)


def _graph(*nodes):
    return ProcessingGraph(graph_id="graph:hr", revision=1, nodes=tuple(nodes))


def test_required_headroom_sums_positive_boosts_only() -> None:
    graph = _graph(
        PreampNode("pre", gain_db=2.0),
        GraphicEqNode(
            "geq",
            layout_id=GraphicEqLayout.MICHI_10_V1,
            gains_db=(6.0, -3.0, 4.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        ),
        ParametricEqNode(
            "peq",
            bands=(
                PeqBand("a", BiquadType.PEAK, 1000.0, 1.0, 5.0, True),
                PeqBand("b", BiquadType.PEAK, 2000.0, 1.0, -9.0, True),
                PeqBand("c", BiquadType.PEAK, 3000.0, 1.0, 7.0, False),
                PeqBand("d", BiquadType.LOW_PASS, 80.0, 0.7, 0.0, True),
            ),
        ),
    )
    # 2.0 + (6.0 + 4.0) + 5.0 ; negative, disabled and gainless excluded.
    assert required_headroom_db(graph) == 17.0


def test_auto_headroom_inserts_one_visible_negative_preamp() -> None:
    graph = _graph(
        GraphicEqNode(
            "geq",
            layout_id=GraphicEqLayout.MICHI_10_V1,
            gains_db=(6.0,) + (0.0,) * 9,
        )
    )
    compensated = with_auto_headroom(graph)
    assert compensated.nodes[0].node_id == AUTO_HEADROOM_NODE_ID
    assert compensated.nodes[0].gain_db == -6.0
    assert len(compensated.nodes) == 2
    # Deterministic and idempotent.
    assert with_auto_headroom(compensated) == compensated
    assert required_headroom_db(graph) == 6.0


def test_no_boost_means_no_hidden_node() -> None:
    graph = _graph(PreampNode("pre", gain_db=-6.0))
    assert with_auto_headroom(graph) is graph
    assert required_headroom_db(graph) == 0.0
