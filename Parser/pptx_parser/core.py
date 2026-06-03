import zipfile
import json
import re

from .ast_node import ASTNode
from .presentation_parser import parse_presentation
from .slide_parser import parse_slide
from .slide_layout_parser import parse_slide_layout
from .slide_master_parser import parse_slide_master
from .core_props_parser import parse_core_props
from .app_props_parser import parse_app_props
from .rels_parser import parse_rels
from .clean import clean_json
from .theme_parser import parse_theme_to_map


def load_pptx(path):
    files = {}
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.endswith(".xml") or name.endswith(".rels"):
                try:
                    files[name] = z.read(name).decode("utf-8")
                except Exception:
                    pass
    return files


def build_context(files):
    context = {
        "files": files,
        "presentation": {},
        "relationships": {},
        "theme_registry": {} 
    }
    
    for name, content in files.items():
        if "ppt/theme/theme" in name and name.endswith(".xml"):

            context["theme_registry"][name] = parse_theme_to_map(content)

    rels_xml = files.get("ppt/_rels/presentation.xml.rels")
    if rels_xml:
        context["relationships"]["presentation"] = parse_rels(rels_xml)
    return context


def parse_pptx(path, clean=True):
    files = load_pptx(path)
    context = build_context(files)
    ast_root = ASTNode(type_="presentation", tag="p:presentation")

    # --- 1. METADATA ---
    core_xml = files.get("docProps/core.xml")
    if core_xml:
        core_props = parse_core_props(core_xml)
        if core_props:
            ast_root.properties["core_properties"] = core_props

    app_xml = files.get("docProps/app.xml")
    if app_xml:
        app_props = parse_app_props(app_xml)
        if app_props:
            ast_root.properties["app_properties"] = app_props

    # --- 2. PRESENTATION.XML ---
    presentation_xml = files.get("ppt/presentation.xml")
    if presentation_xml:
        presentation_data = parse_presentation(presentation_xml, context)
        if presentation_data:
            if "slide_size" in presentation_data:
                ast_root.properties["slide_size"] = presentation_data["slide_size"]
            context["presentation"]["slide_rIds"] = presentation_data.get("slide_rIds", [])
            context["presentation"]["slide_master_rIds"] = presentation_data.get("slide_master_rIds", [])

    presentation_rels = context["relationships"].get("presentation", {})

    # --- 3. ĐỌC SLIDE MASTERS ---
    master_rids = context["presentation"].get("slide_master_rIds", [])
    if master_rids and presentation_rels:
        for r_id in master_rids:
            target = presentation_rels.get(r_id, {}).get("Target")
            if target:
                master_path = f"ppt/{target}"
                master_xml = files.get(master_path)
                if master_xml:
                    master_node = parse_slide_master(master_xml, master_path, context)
                    if master_node:
                        ast_root.add_child(master_node)

    # --- 4. ĐỌC SLIDE LAYOUTS (MỚI THÊM) ---
    # Layouts không được list ở presentation.xml, mà phải quyét từ thư mục
    layout_files = [f for f in files.keys() if f.startswith("ppt/slideLayouts/slideLayout") and f.endswith(".xml")]
    for layout_file in layout_files:
        layout_node = parse_slide_layout(files[layout_file], layout_file, context)
        if layout_node:
            ast_root.add_child(layout_node)

    # --- 5. ĐỌC SLIDES ---
    slide_rids = context["presentation"].get("slide_rIds", [])
    if slide_rids and presentation_rels:
        for index, r_id in enumerate(slide_rids):
            target = presentation_rels.get(r_id, {}).get("Target")
            if target:
                slide_path = f"ppt/{target}"
                slide_xml = files.get(slide_path)
                if slide_xml:
                    slide_index = index + 1
                    slide_node = parse_slide(slide_xml, slide_path, slide_index, context)
                    if slide_node:
                        ast_root.add_child(slide_node)

    data = ast_root.to_dict()
    if clean:
        data = clean_json(data)
    return data


def parse_pptx_to_file(input_path, output_path, clean=True):
    data = parse_pptx(input_path, clean=clean)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data