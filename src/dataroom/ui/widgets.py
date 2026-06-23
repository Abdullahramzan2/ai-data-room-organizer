"""Reusable Streamlit widgets."""

from __future__ import annotations

import streamlit as st

from dataroom.ui.pickers import browse_folder


def _apply_pending_folder_pick(state_key: str) -> None:
    pending_key = f"_browse_pick_{state_key}"
    if pending_key not in st.session_state:
        return
    st.session_state[state_key] = st.session_state.pop(pending_key)


def folder_path_field(
    label: str,
    state_key: str,
    *,
    sidebar: bool = False,
    stacked: bool = False,
) -> None:
    """Text field plus Browse button bound to ``st.session_state[state_key]``."""
    _apply_pending_folder_pick(state_key)

    ui = st.sidebar if sidebar else st
    if stacked or sidebar:
        ui.text_input(label, key=state_key)
        if ui.button("Browse…", key=f"browse_{state_key}", use_container_width=True):
            current = str(st.session_state.get(state_key, "") or "")
            picked = browse_folder(current, title=f"Select {label.lower()}")
            if picked:
                st.session_state[f"_browse_pick_{state_key}"] = picked
                st.rerun()
        return

    path_col, btn_col = ui.columns([5, 1], vertical_alignment="bottom")
    with path_col:
        ui.text_input(label, key=state_key)
    with btn_col:
        if ui.button("Browse", key=f"browse_{state_key}", use_container_width=True):
            current = str(st.session_state.get(state_key, "") or "")
            picked = browse_folder(current, title=f"Select {label.lower()}")
            if picked:
                st.session_state[f"_browse_pick_{state_key}"] = picked
                st.rerun()
