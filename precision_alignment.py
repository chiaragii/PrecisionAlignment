from copy import copy
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pandas as pd
from pm4py.algo.conformance.alignments.petri_net import algorithm as petri_alignments
from pm4py.objects import log as log_lib
from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.objects.petri_net import semantics
from pm4py.objects.petri_net.obj import Marking, PetriNet
from pm4py.objects.petri_net.utils import (
    align_utils as pn_align_utils,
    check_soundness,
)
from pm4py.statistics.start_activities.log.get import get_start_activities
from pm4py.util import constants, exec_utils, variants_util


class Parameters(Enum):
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY
    CASE_ID_KEY = constants.PARAMETER_CONSTANT_CASEID_KEY
    TOKEN_REPLAY_VARIANT = "token_replay_variant"
    CLEANING_TOKEN_FLOOD = "cleaning_token_flood"
    SHOW_PROGRESS_BAR = "show_progress_bar"
    MULTIPROCESSING = "multiprocessing"
    CORES = "cores"


def _extract_model_sequence(
    alignment: List[Tuple[Tuple[str, str], Tuple[str, str]]]
) -> List[str]:
    seq: List[str] = []
    for move in alignment:
        if move[0][1] != ">>":
            label = move[1][1]
            if label is not None and label != ">>":
                seq.append(label)
    return seq


def _update_prefix_stats(
    seq: List[str],
    weight: int,
    prefixes: Dict[str, Set[str]],
    prefix_count: Dict[str, int],
) -> None:
    if not seq:
        return

    current_prefix = None
    for i, activity in enumerate(seq[:-1]):
        current_prefix = activity if current_prefix is None else f"{current_prefix},{activity}"

        next_act = seq[i + 1]

        prefixes.setdefault(current_prefix, set()).add(next_act)
        prefix_count[current_prefix] = prefix_count.get(current_prefix, 0) + weight


def apply(
    log: Union[EventLog, EventStream, pd.DataFrame],
    net: PetriNet,
    im: Marking,
    fm: Marking,
    parameters: Optional[Dict[Union[str, Parameters], Any]] = None,
) -> float:
    if parameters is None:
        parameters = {}

    if not check_soundness.check_easy_soundness_net_in_fin_marking(net, im, fm):
        raise ValueError(
            "Align ETC precision can only be applied on a Petri net that is "
            "a sound WF-net (easy sound)."
        )

    activity_key = exec_utils.get_param_value(
        Parameters.ACTIVITY_KEY, parameters, log_lib.util.xes.DEFAULT_NAME_KEY
    )
    case_id_key = exec_utils.get_param_value(
        Parameters.CASE_ID_KEY, parameters, constants.CASE_CONCEPT_NAME
    )

    debug_level = parameters.get("debug_level", 0)

    import pm4py

    variants = pm4py.get_variants(log, activity_key)
    variant_keys = list(variants.keys())

    red_log = EventLog()
    for var in variant_keys:
        red_log.append(variants_util.variant_to_trace(var, parameters=parameters))

    align_params = copy(parameters)
    align_params["ret_tuple_as_trans_desc"] = True

    aligned_traces = petri_alignments.apply(red_log, net, im, fm, parameters=align_params)

    trans_by_name = {t.name: t for t in net.transitions}

    prefixes: Dict[str, Set[str]] = {}
    prefix_count: Dict[str, int] = {}

    for variant_idx, aligned in enumerate(aligned_traces):
        alignment = aligned["alignment"]
        seq = _extract_model_sequence(alignment)

        freq = len(variants[variant_keys[variant_idx]])
        _update_prefix_stats(seq, freq, prefixes, prefix_count)

    precision = 1.0
    sum_ee = 0
    sum_at = 0

    visited_markings: Dict[Marking, Set[str]] = {}
    visited_prefixes: Set[str] = set()
    escaping_dict: Dict[str, Set[Str]] = {}

    for variant_idx, aligned in enumerate(aligned_traces):
        alignment = aligned["alignment"]

        marking = copy(im)
        prefix = None

        idxs = [i for i, m in enumerate(alignment) if m[0][1] != ">>"]
        if not idxs:
            continue
        last_log_idx = idxs[-1]

        for i in range(last_log_idx):
            move = alignment[i]

            if move[0][1] != ">>":
                transition = trans_by_name[move[0][1]]
                marking = semantics.execute(transition, net, marking)

            if move[1][1] != None and move[1][1] != ">>":
                activity = move[1][1]
                prefix = activity if prefix is None else f"{prefix},{activity}"

                if prefix not in visited_prefixes:
                    if marking in visited_markings:
                        enabled_vis = visited_markings[marking]
                    else:
                        enabled_vis = {
                            t.label
                            for t in pn_align_utils.get_visible_transitions_eventually_enabled_by_marking(
                                net, marking
                            )
                            if t.label is not None
                        }
                        visited_markings[marking] = enabled_vis

                    log_transitions = prefixes.get(prefix, set())
                    escaping = enabled_vis.difference(log_transitions)
                    escaping_dict.setdefault(prefix, set()).update(escaping)

                    multiplicity = prefix_count.get(prefix, 0)

                    sum_at += len(enabled_vis) * multiplicity
                    sum_ee += len(escaping) * multiplicity

                    visited_prefixes.add(prefix)

    start_acts = set(get_start_activities(log, parameters=parameters))
    enabled_ini = {
        t.label
        for t in pn_align_utils.get_visible_transitions_eventually_enabled_by_marking(
            net, im
        )
        if t.label is not None
    }
    diff_ini = enabled_ini.difference(start_acts)

    n_traces = len(log) if isinstance(log, EventLog) else log[case_id_key].nunique()
    sum_at += len(enabled_ini) * n_traces
    sum_ee += len(diff_ini) * n_traces

    if sum_at > 0:
        precision = 1.0 - float(sum_ee) / float(sum_at)

    if debug_level > 0:
        print(
            f"[Align ‘ETC-Precision‘ Aligned]  AT={sum_at}  EE={sum_ee}  precision={precision:.5f}"
        )

    return precision
