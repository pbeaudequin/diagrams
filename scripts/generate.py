import os
import sys
from typing import Iterable

from jinja2 import Environment, FileSystemLoader, Template

import config as cfg
from . import app_root_dir, doc_root_dir, resource_dir, template_dir

_usage = "Usage: generate.py <onprem|aws|gcp|azure|k8s|alibabacloud|oci|programming>"


def load_tmpl(tmpl: str) -> Template:
    env = Environment(loader=FileSystemLoader(template_dir()))
    env.filters["up_or_title"] = up_or_title
    return env.get_template(tmpl)


def up_or_title(pvd: str, s: str) -> str:
    if s in cfg.UPPER_WORDS.get(pvd, ()):
        return s.upper()
    if s in cfg.TITLE_WORDS.get(pvd, {}):
        return cfg.TITLE_WORDS[pvd][s]
    return s.title()

# TODO: independent function for generating all pvd/typ/paths pairs
def gen_class_meta(path: str) -> dict:
    base = os.path.splitext(path)[0]
    name = "".join([up_or_title(pvd, s) for s in base.split("-")])
    return {"name": name, "icon": path}
    
def gen_classes(pvd: str, typ: str, paths: Iterable[str]) -> str:
    """Generate all service node classes based on resources paths with class templates."""
    tmpl = load_tmpl(cfg.TMPL_MODULE)

    metas = map(gen_class_meta, paths)
    aliases = cfg.ALIASES[pvd][typ] if typ in cfg.ALIASES[pvd] else {}
    return tmpl.render(pvd=pvd, typ=typ, metas=metas, aliases=aliases)


def gen_apidoc(pvd: str, typ_paths: dict, template_file: str) -> str:
    tmpl = load_tmpl(template_file)

    typ_classes = {}
    for typ, paths in typ_paths.items():
        typ_classes[typ] = []
        for metas in map(gen_class_meta, paths):
            name = metas.get('name')
            metas['alias'] = cfg.ALIASES[pvd].get(typ, {}).get(name)
            typ_classes[typ].append(metas)
    return tmpl.render(pvd=pvd, typ_classes=typ_classes)


def make_module(pvd: str, typ: str, classes: str) -> None:
    """Create a module file"""
    mod_path = os.path.join(app_root_dir(pvd), f"{typ}.py")
    with open(mod_path, "w+") as f:
        f.write(classes)


def make_apidoc(pvd: str, content: str) -> None:
    """Create an api documentation file"""
    mod_path = os.path.join(doc_root_dir(), f"{pvd}.md")
    with open(mod_path, "w+") as f:
        f.write(content)

def make_icongallery(pvd: str, content: str) -> None:
    """Append to icon gallery md file"""
    mod_path = os.path.join(doc_root_dir(), f"icon_gallery.md")
    with open(mod_path, "a+") as f:
        f.write(content)


def generate(pvd: str) -> None:
    """Generates a service node classes."""
    typ_paths = {}
    for root, _, files in os.walk(resource_dir(pvd)):
        # Extract the names and paths from resources.
        files.sort()
        pngs = list(filter(lambda f: f.endswith(".png"), files))
        paths = list(filter(lambda f: "rounded" not in f, pngs))

        # Skip the top-root directory.
        typ = os.path.basename(root)
        if typ == pvd:
            continue

        classes = gen_classes(pvd, typ, paths)
        make_module(pvd, typ, classes)

        typ_paths[typ] = paths
    # Build API documentation
    apidoc = gen_apidoc(pvd, typ_paths, cfg.TMPL_APIDOC)
    make_apidoc(pvd, apidoc)

    # Build icon gallery documentation
    apidoc = gen_apidoc(pvd, typ_paths, cfg.TMPL_ICON_GALLERY)
    make_icongallery(pvd, apidoc)


if __name__ == "__main__":
    pvd = sys.argv[1]
    if pvd not in cfg.PROVIDERS:
        sys.exit()
    generate(pvd)
