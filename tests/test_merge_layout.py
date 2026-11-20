from idp.merge_layout import snap_box, snap_layout_pages


def _item(label, text, x, y, w, h):
    seg = {"x": x, "y": y, "w": w, "h": h, "r": None, "label": label}
    return {"value": text, "bbox": dict(seg), "layout_segments": [dict(seg)]}


def test_snap_box_needs_matching_words():
    words = [(0.11, 0.21, 0.2, 0.23, "Hello"), (0.22, 0.21, 0.3, 0.23, "world")]
    box = {"x": 0.1, "y": 0.2, "w": 0.25, "h": 0.05}
    new = snap_box(box, "Hello world", words)
    assert (new["x"], new["y"], round(new["w"], 2), round(new["h"], 2)) == (0.11, 0.21, 0.19, 0.02)
    assert snap_box(box, "Something else entirely", words) is None


def test_each_word_snaps_to_one_box_and_tables_stay():
    words = [(0.11, 0.21, 0.2, 0.23, "Title"), (0.11, 0.24, 0.3, 0.26, "Body"), (0.5, 0.5, 0.6, 0.52, "42")]
    pages = [{"items": [_item("Title", "Title", 0.1, 0.2, 0.25, 0.035),
                        _item("Text", "Body", 0.1, 0.235, 0.25, 0.03),
                        _item("Table", "<table><tr><td>42</td></tr></table>", 0.45, 0.45, 0.2, 0.1)]}]
    assert snap_layout_pages(pages, words) == 2
    title, body, table = (it["layout_segments"][0] for it in pages[0]["items"])
    assert round(title["y"] + title["h"], 2) == 0.23 and round(body["y"], 2) == 0.24
    assert table["x"] == 0.45
    assert pages[0]["items"][0]["bbox"]["y"] == title["y"]


def test_transplant_layout_converts_kdl_items():
    from idp.merge_layout import transplant_layout
    target = [{"page_number": 1, "width": 1000, "height": 1400, "items": [_item("Text", "old", 0, 0, 1, 1)]}]
    seg = {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.1, "r": None, "label": "Chart"}
    source = [{"page_number": 1, "items": [{"type": "Chart", "md": "chart text", "value": "", "bbox": dict(seg),
                                            "layout_segments": [dict(seg)]}]}]
    assert transplant_layout(target, source) == 1
    it = target[0]["items"][0]
    assert it["value"] == "chart text" and it["layout_segments"][0]["label"] == "Picture"
    assert target[0]["width"] == 1000
