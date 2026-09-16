"""Screen Mental Map & Cognitive Attention Engine.

Maintains a persistent, layered mental model of the Windows screen, tracks agent attention,
fuses UIAutomation and WinRT OCR perception, and derives actionable affordances.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
import math
import re


class SpatialScreenLayer(str, Enum):
    """Hierarchical spatial layers comprising the Windows desktop ecosystem."""
    LAYER_0_DESKTOP = "desktop_shell"          # Desktop wallpaper, taskbar, system tray
    LAYER_1_INACTIVE = "inactive_windows"      # Background application windows (Z-stack)
    LAYER_2_ACTIVE = "active_workspace"        # Currently focused application window
    LAYER_3_MODAL = "modal_overlays"           # Dialog boxes, context menus, alert popups
    LAYER_4_ZONES = "functional_zones"         # Functional layout zones within active workspace


class FunctionalZone(str, Enum):
    """Functional layout zones within an application window."""
    HEADER = "header"              # Titlebar, window controls, top menu
    NAVIGATION = "navigation"      # Omnibox, breadcrumbs, tab strip, toolbars
    CONTENT = "content"            # Main work canvas, viewport, search results
    SIDEBAR = "sidebar"            # Left/Right navigation rails or palettes
    FOOTER = "footer"              # Status bar, pagination, bottom actions
    MODAL = "modal"                # Floating popup or dialog content


class SemanticRole(str, Enum):
    """Semantic functional role of an interactive or perceived element."""
    BUTTON = "button"
    INPUT = "input"
    SEARCH_BOX = "search_box"
    TAB = "tab"
    CARD = "card"
    LINK = "link"
    MENU_ITEM = "menu_item"
    DIALOG = "dialog"
    TEXT = "text"
    IMAGE = "image"
    UNKNOWN = "unknown"


class SemanticUIElement:
    """Unified semantic UI element fusing UIAutomation and OCR detections."""

    def __init__(
        self,
        element_id: str,
        role: SemanticRole,
        text: str,
        bounds: Dict[str, int],
        zone: FunctionalZone = FunctionalZone.CONTENT,
        is_enabled: bool = True,
        is_focused: bool = False,
        confidence: float = 1.0,
        source: str = "fused",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.element_id = element_id
        self.role = role
        self.text = text.strip()
        self.bounds = bounds  # {'x': ..., 'y': ..., 'width': ..., 'height': ...}
        self.zone = zone
        self.is_enabled = is_enabled
        self.is_focused = is_focused
        self.confidence = confidence
        self.source = source
        self.metadata = metadata or {}

    @property
    def center(self) -> Tuple[int, int]:
        cx = self.bounds.get("x", 0) + self.bounds.get("width", 0) // 2
        cy = self.bounds.get("y", 0) + self.bounds.get("height", 0) // 2
        return cx, cy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "role": self.role.value,
            "text": self.text,
            "bounds": self.bounds,
            "center": list(self.center),
            "zone": self.zone.value,
            "is_enabled": self.is_enabled,
            "is_focused": self.is_focused,
            "confidence": round(self.confidence, 2),
            "source": self.source,
            "metadata": self.metadata,
        }


class AttentionState:
    """Tracks the agent's active cognitive attention on the screen."""

    def __init__(
        self,
        focused_window_handle: Optional[int] = None,
        focused_window_title: str = "",
        focused_element_id: Optional[str] = None,
        active_zone: FunctionalZone = FunctionalZone.CONTENT,
        attention_target: Optional[str] = None,
        action_affordances: Optional[List[Dict[str, Any]]] = None,
    ):
        self.focused_window_handle = focused_window_handle
        self.focused_window_title = focused_window_title
        self.focused_element_id = focused_element_id
        self.active_zone = active_zone
        self.attention_target = attention_target
        self.action_affordances = action_affordances or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "focused_window_handle": self.focused_window_handle,
            "focused_window_title": self.focused_window_title,
            "focused_element_id": self.focused_element_id,
            "active_zone": self.active_zone.value,
            "attention_target": self.attention_target,
            "action_affordances": self.action_affordances,
        }


class ScreenMentalMap:
    """Synthesizes physical desktop metrics, window Z-order, and UI perceptions into a cognitive mental model."""

    def __init__(
        self,
        active_window: Optional[Dict[str, Any]] = None,
        inactive_windows: Optional[List[Dict[str, Any]]] = None,
        modals: Optional[List[Dict[str, Any]]] = None,
        elements: Optional[List[SemanticUIElement]] = None,
        attention: Optional[AttentionState] = None,
    ):
        self.active_window = active_window or {}
        self.inactive_windows = inactive_windows or []
        self.modals = modals or []
        self.elements = elements or []
        self.attention = attention or AttentionState()

    @classmethod
    def classify_zone(cls, y: int, height: int, x: int, width: int, win_w: int, win_h: int) -> FunctionalZone:
        """Heuristically partitions window space into functional zones."""
        if win_h <= 0 or win_w <= 0:
            return FunctionalZone.CONTENT

        rel_y = y / win_h
        rel_h = height / win_h

        # Top 12% is header / title / tab strip
        if rel_y < 0.12:
            return FunctionalZone.HEADER
        # Next 12% is navigation / omnibox / toolbars
        if rel_y < 0.24:
            return FunctionalZone.NAVIGATION
        # Bottom 7% is status bar / footer
        if rel_y + rel_h > 0.93:
            return FunctionalZone.FOOTER
        # Left/Right 18% if tall can be sidebar
        rel_x = x / win_w
        if (rel_x < 0.18 and width / win_w < 0.25) or (rel_x > 0.82 and width / win_w < 0.25):
            return FunctionalZone.SIDEBAR

        return FunctionalZone.CONTENT

    @classmethod
    def infer_role(cls, raw_type: str, text: str, bounds: Dict[str, int]) -> SemanticRole:
        """Determines the semantic role of an element based on text, control type, and shape."""
        t_clean = text.lower().strip()
        ctrl = raw_type.lower().replace("controltype.", "")

        if "button" in ctrl or any(b in t_clean for b in ["submit", "ok", "cancel", "apply", "save", "delete", "close"]):
            return SemanticRole.BUTTON
        if "edit" in ctrl or "textbox" in ctrl:
            if any(s in t_clean for s in ["search", "find", "query", "google", "ask"]):
                return SemanticRole.SEARCH_BOX
            return SemanticRole.INPUT
        if "tab" in ctrl:
            return SemanticRole.TAB
        if "link" in ctrl or "http" in t_clean or "www." in t_clean:
            return SemanticRole.LINK
        if "menu" in ctrl:
            return SemanticRole.MENU_ITEM
        if "dialog" in ctrl or "window" in ctrl:
            return SemanticRole.DIALOG
        if "text" in ctrl or "label" in ctrl:
            if len(t_clean) < 30 and any(s in t_clean for s in ["search", "find"]):
                return SemanticRole.SEARCH_BOX
            return SemanticRole.TEXT

        # Infer from shape & text if type is unknown
        w = bounds.get("width", 0)
        h = bounds.get("height", 0)
        if h > 0 and 2.0 <= (w / h) <= 6.0 and len(t_clean) < 25 and any(b in t_clean for b in ["search", "sign in", "login", "next", "read more"]):
            return SemanticRole.BUTTON

        return SemanticRole.UNKNOWN

    @classmethod
    def _normalize_window(cls, win: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes a raw window record into the internal ``{handle,title,state,bounds}`` shape."""
        hwnd = win.get("Handle") or win.get("handle")
        title = win.get("Title") or win.get("title") or ""
        state = win.get("State") or win.get("state") or "Normal"
        bounds = win.get("Bounds") or win.get("bounds") or {}

        w_dict = {"x": 0, "y": 0, "width": 1920, "height": 1080}
        if isinstance(bounds, dict):
            w_dict.update(bounds)
        elif isinstance(bounds, str) and "(" in bounds:
            match = re.search(r'(-?\d+),\s*(-?\d+)\s*\((-?\d+)x(-?\d+)\)', bounds)
            if match:
                w_dict = {
                    "x": int(match.group(1)),
                    "y": int(match.group(2)),
                    "width": int(match.group(3)),
                    "height": int(match.group(4)),
                }
        return {"handle": hwnd, "title": title, "state": state, "bounds": w_dict}

    @staticmethod
    def _coerce_ocr_lines(ocr_lines: Any) -> List[str]:
        """Accepts either plain strings or WinRT OCR dicts and returns clean strings."""
        if not ocr_lines:
            return []
        if isinstance(ocr_lines, dict):
            ocr_lines = ocr_lines.get("Lines") or ocr_lines.get("lines") or []
        normalized: List[str] = []
        for line in ocr_lines:
            if isinstance(line, str):
                normalized.append(line)
            elif isinstance(line, dict):
                text = line.get("Text") or line.get("text") or ""
                if text:
                    normalized.append(str(text))
        return normalized

    @classmethod
    def build_from_perceptions(
        cls,
        windows: List[Dict[str, Any]],
        target_hwnd: Optional[int] = None,
        uia_elements: Optional[List[Dict[str, Any]]] = None,
        ocr_lines: Optional[List[str]] = None,
    ) -> "ScreenMentalMap":
        """Builds a multi-layered screen mental map from windows, UIAutomation, and OCR data."""
        # Accept the full inspect result dict as well as a bare element list.
        if isinstance(uia_elements, dict):
            uia_elements = (
                uia_elements.get("Elements")
                or uia_elements.get("elements")
                or uia_elements.get("Items")
                or []
            )
        clean_ocr_lines = cls._coerce_ocr_lines(ocr_lines)

        active_win = None
        inactive_wins = []
        modals = []

        # 1. Partition Windows into Active, Inactive, and Modals
        for win in windows:
            win_summary = cls._normalize_window(win)
            title = win_summary["title"]
            state = win_summary["state"]
            hwnd = win_summary["handle"]
            w_dict = win_summary["bounds"]

            # Check if modal/dialog
            if any(m in title.lower() for m in ["dialog", "run", "confirm", "alert", "error", "open file", "save as"]):
                modals.append(win_summary)

            if target_hwnd and hwnd == target_hwnd:
                active_win = win_summary
            elif not active_win and state != "Minimized" and w_dict.get("x", 0) >= 0:
                active_win = win_summary
            else:
                inactive_wins.append(win_summary)

        if not active_win and windows:
            active_win = cls._normalize_window(windows[0])

        win_w = active_win.get("bounds", {}).get("width", 1920) if active_win else 1920
        win_h = active_win.get("bounds", {}).get("height", 1080) if active_win else 1080
        win_x = active_win.get("bounds", {}).get("x", 0) if active_win else 0
        win_y = active_win.get("bounds", {}).get("y", 0) if active_win else 0

        # 2. Fuse Elements
        semantic_elements: List[SemanticUIElement] = []
        elem_idx = 1

        # A. Process UIAutomation Elements
        if uia_elements:
            for el in uia_elements:
                if not isinstance(el, dict):
                    continue
                name = el.get("Name") or el.get("name") or ""
                auto_id = el.get("AutomationId") or el.get("automation_id") or ""
                c_type = el.get("ControlType") or el.get("control_type") or "Unknown"
                text = name or auto_id

                # Prefer explicit center/size; fall back to a BoundingRectangle.
                cx = el.get("CenterX") or el.get("center_x")
                cy = el.get("CenterY") or el.get("center_y")
                w = el.get("Width") or el.get("width")
                h = el.get("Height") or el.get("height")
                if cx is None or cy is None:
                    rect = el.get("BoundingRectangle") or el.get("bounding_rectangle") or {}
                    if isinstance(rect, dict):
                        rx = rect.get("X", rect.get("Left", rect.get("x", 0)))
                        ry = rect.get("Y", rect.get("Top", rect.get("y", 0)))
                        rw = rect.get("Width", rect.get("width", 0))
                        rh = rect.get("Height", rect.get("height", 0))
                        cx = rx + (rw / 2)
                        cy = ry + (rh / 2)
                        w = w or rw
                        h = h or rh
                cx = cx or 0
                cy = cy or 0
                w = w or 80
                h = h or 30
                bx = int(cx - (w // 2))
                by = int(cy - (h // 2))

                bounds = {"x": bx, "y": by, "width": int(w), "height": int(h)}
                # Zone classification expects window-relative coordinates.
                zone = cls.classify_zone(by - win_y, int(h), bx - win_x, int(w), win_w, win_h)
                role = cls.infer_role(c_type, text, bounds)

                semantic_elements.append(
                    SemanticUIElement(
                        element_id=f"elem-uia-{elem_idx}",
                        role=role,
                        text=text,
                        bounds=bounds,
                        zone=zone,
                        is_enabled=bool(el.get("IsEnabled", el.get("is_enabled", True))),
                        is_focused=bool(el.get("HasKeyboardFocus", el.get("is_focused", False))),
                        source="uia",
                        metadata={"automation_id": auto_id, "control_type": c_type},
                    )
                )
                elem_idx += 1

        # B. Process WinRT OCR Text Lines (Particularly critical for Class B Electron/Chromium apps)
        if clean_ocr_lines:
            line_count = len(clean_ocr_lines)
            for i, line in enumerate(clean_ocr_lines):
                cleaned = line.strip()
                if not cleaned or cleaned.startswith("+--") or cleaned.startswith("|--"):
                    continue

                # Strip table border pipes if present
                clean_text = cleaned.strip("|").strip()
                if not clean_text:
                    continue

                # Approximate vertical layout based on line sequence index
                approx_y = int((i / max(1, line_count)) * win_h)
                approx_h = max(20, int(win_h / max(1, line_count * 1.5)))
                approx_w = min(win_w - 40, max(120, len(clean_text) * 12))
                approx_x = 20

                bounds = {"x": approx_x, "y": approx_y, "width": approx_w, "height": approx_h}
                zone = cls.classify_zone(approx_y, approx_h, approx_x, approx_w, win_w, win_h)
                role = cls.infer_role("Text", clean_text, bounds)

                # Avoid duplicate if an exact UIA match already registered
                if not any(e.text.lower() == clean_text.lower() for e in semantic_elements):
                    semantic_elements.append(
                        SemanticUIElement(
                            element_id=f"elem-ocr-{elem_idx}",
                            role=role,
                            text=clean_text,
                            bounds=bounds,
                            zone=zone,
                            source="ocr",
                            metadata={"line_index": i},
                        )
                    )
                    elem_idx += 1

        # 3. Derive Action Affordances & Attention
        affordances = []
        focused_elem_id = None
        for el in semantic_elements:
            if el.is_focused:
                focused_elem_id = el.element_id

            if el.role in (SemanticRole.BUTTON, SemanticRole.TAB, SemanticRole.MENU_ITEM, SemanticRole.LINK):
                affordances.append({
                    "action": "CLICK",
                    "target_id": el.element_id,
                    "target_text": el.text,
                    "center": list(el.center),
                    "zone": el.zone.value,
                    "priority": "HIGH" if el.role in (SemanticRole.BUTTON, SemanticRole.TAB) else "NORMAL",
                })
            elif el.role in (SemanticRole.INPUT, SemanticRole.SEARCH_BOX):
                affordances.append({
                    "action": "TYPE",
                    "target_id": el.element_id,
                    "target_text": el.text,
                    "center": list(el.center),
                    "zone": el.zone.value,
                    "priority": "HIGH",
                })

        # Add generic scroll affordance for content zone
        affordances.append({
            "action": "SCROLL",
            "zone": FunctionalZone.CONTENT.value,
            "direction": "DOWN",
            "priority": "LOW",
        })

        attention = AttentionState(
            focused_window_handle=active_win.get("handle") if active_win else None,
            focused_window_title=active_win.get("title", "") if active_win else "",
            focused_element_id=focused_elem_id,
            active_zone=FunctionalZone.CONTENT if not modals else FunctionalZone.MODAL,
            attention_target=semantic_elements[0].text if semantic_elements else None,
            action_affordances=affordances[:15],  # Top 15 affordances
        )

        return cls(
            active_window=active_win,
            inactive_windows=inactive_wins,
            modals=modals,
            elements=semantic_elements,
            attention=attention,
        )

    def diff(self, previous_map: "ScreenMentalMap") -> Dict[str, Any]:
        """Calculates state delta between this map and a previous map."""
        prev_texts = {e.text.lower(): e for e in previous_map.elements}
        curr_texts = {e.text.lower(): e for e in self.elements}

        appeared = [e.to_dict() for t, e in curr_texts.items() if t not in prev_texts]
        disappeared = [e.to_dict() for t, e in prev_texts.items() if t not in curr_texts]

        title_changed = (self.active_window.get("title") != previous_map.active_window.get("title"))

        return {
            "title_changed": title_changed,
            "previous_title": previous_map.active_window.get("title", ""),
            "current_title": self.active_window.get("title", ""),
            "appeared_count": len(appeared),
            "disappeared_count": len(disappeared),
            "appeared_samples": [a["text"] for a in appeared[:5]],
            "disappeared_samples": [d["text"] for d in disappeared[:5]],
            "has_modals": bool(self.modals),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spatial_layers": {
                "layer_0_desktop": {"status": "Active"},
                "layer_1_inactive_windows": self.inactive_windows,
                "layer_2_active_workspace": self.active_window,
                "layer_3_modal_overlays": self.modals,
                "layer_4_functional_zones": {
                    zone.value: len([e for e in self.elements if e.zone == zone])
                    for zone in FunctionalZone
                },
            },
            "attention": self.attention.to_dict(),
            "element_count": len(self.elements),
            "elements": [e.to_dict() for e in self.elements],
        }

    def to_markdown_summary(self) -> str:
        """Renders an executive cognitive screen summary formatted for LLMs."""
        title = self.active_window.get("title", "Unknown Window")
        hwnd = self.active_window.get("handle", "N/A")
        bounds = self.active_window.get("bounds", {})

        md = [
            f"### Cognitive Screen Mental Map: {title} (HWND: {hwnd})",
            f"- **Active Bounds**: {bounds.get('width', 0)}x{bounds.get('height', 0)} at ({bounds.get('x', 0)}, {bounds.get('y', 0)})",
            f"- **Active Modals**: {len(self.modals)} detected",
            f"- **Total Semantic Elements**: {len(self.elements)}",
            "",
            "#### Functional Zones Breakdown:",
        ]

        for zone in FunctionalZone:
            zone_elements = [e for e in self.elements if e.zone == zone]
            if zone_elements:
                sample_texts = ", ".join(f"`{e.text[:25]}` ({e.role.value})" for e in zone_elements[:4])
                md.append(f"- **{zone.value.upper()}** ({len(zone_elements)} items): {sample_texts}")

        md.append("")
        md.append("#### Next Action Affordances (Attention Opportunities):")
        for aff in self.attention.action_affordances[:6]:
            target = aff.get("target_text") or aff.get("zone") or "Canvas"
            md.append(f"- `[{aff['action']}]` **{target}** (Priority: {aff['priority']}, Center: {aff.get('center', [])})")

        return "\n".join(md)
