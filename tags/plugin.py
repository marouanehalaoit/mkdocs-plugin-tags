# --------------------------------------------
# Main part of the plugin
#
# JL Diaz (c) 2019
# MIT License
# --------------------------------------------
from collections  import defaultdict
from pathlib import Path
import os
import yaml
import jinja2
from mkdocs.structure.files import File
from mkdocs.structure.nav import Section
from mkdocs.plugins import BasePlugin
from mkdocs.config.config_options import Type


class TagsPlugin(BasePlugin):
    """
    Creates "tags.md" file containing a list of the pages grouped by tags

    It uses the info in the YAML metadata of each page, for the pages which
    provide a "tags" keyword (whose value is a list of strings)
    """

    config_scheme = (
        ('tags_filename', Type(str, default='tags.md')),
        ('tags_folder', Type(str, default='aux')),
        ('tags_template', Type(str)),
    )

    def __init__(self):
        self.metadata = []
        self.tags_filename = "tags.md"
        self.tags_folder = "aux"
        self.tags_template = None
        self.tag_pages_filename_template = "tag.{tag}.md"

    def on_nav(self, nav, config, files):
        # nav.items.insert(1, nav.items.pop(-1))
        pass

    def on_config(self, config):
        # Re assign the options
        self.tags_filename = Path(self.config.get("tags_filename") or self.tags_filename)
        self.tags_folder = Path(self.config.get("tags_folder") or self.tags_folder)
        # Make sure that the tags folder is absolute, and exists
        if not self.tags_folder.is_absolute():
            self.tags_folder = Path(config["docs_dir"]) / ".." / self.tags_folder
        if not self.tags_folder.exists():
            self.tags_folder.mkdir(parents=True)

        if self.config.get("tags_template"):
            self.tags_template = Path(self.config.get("tags_template"))

    def on_files(self, files, config):
        # Scan the list of files to extract tags from meta
        for f in files:
            if not f.src_path.endswith(".md"):
                continue
            self.metadata.append(get_metadata(f.src_path, config["docs_dir"]))

        # Create new files with tags
        generated_files = self.generate_files()

        # New file to add to the build
        for generated_file in generated_files:
            newfile = File(
                path=str(generated_file),
                src_dir=str(self.tags_folder),
                dest_dir=config["site_dir"],
                use_directory_urls=False
            )
            files.append(newfile)

    def generate_files(self):
        all_generated_files = []

        # Get aggregated data
        data = self.__get_aggregated_data()

        # Dict that maps tag with the file containing its pages
        d = dict()

        # 1 - Create pages per tag files
        for tag, pages in data:
            filename = self.tag_pages_filename_template.format(tag=tag)
            templ_path = Path(__file__).parent  / Path("templates")
            environment = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(templ_path))
                )
            templ = environment.get_template("tag-pages.md.template")
            output_text = templ.render(tag=tag, pages=pages)
            file_path = str(self.tags_folder / filename)
            self.__write_file(output_text, file_path)
            d[tag] = filename
            all_generated_files.append(filename)
        
        # 2 - Create the global tags file
        if self.tags_template is None:
            templ_path = Path(__file__).parent  / Path("templates")
            environment = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(templ_path))
                )
            templ = environment.get_template("tags.md.template")
        else:
            environment = jinja2.Environment(
                loader=jinja2.FileSystemLoader(searchpath=str(self.tags_template.parent))
            )
            templ = environment.get_template(str(self.tags_template.name))
        output_text = templ.render(data=d.items())
        file_path = str(self.tags_folder / self.tags_filename)
        self.__write_file(output_text, file_path)
        all_generated_files.append(self.tags_filename)

        return all_generated_files

    def __get_aggregated_data(self):
        sorted_meta = sorted(self.metadata, key=lambda e: e.get("year", 5000) if e else 0)
        tag_dict = defaultdict(list)
        for e in sorted_meta:
            if not e:
                continue
            if "title" not in e:
                e["title"] = "Untitled"
            tags = e.get("tags", [])
            if tags is not None:
                for tag in tags:
                    tag_dict[tag].append(e)
        return sorted(tag_dict.items(), key=lambda t: t[0].lower())

    def __write_file(self, data, file_path):
        with open(file_path, "w") as f:
            f.write(data)

# Helper functions

def get_metadata(name, path):
    # Extract metadata from the yaml at the beginning of the file
    def extract_yaml(f):
        result = []
        c = 0
        for line in f:
            if line.strip() == "---":
                c +=1
                continue
            if c==2:
                break
            if c==1:
                result.append(line)
        return "".join(result)

    filename = Path(path) / Path(name)
    with filename.open() as f:
        metadata = extract_yaml(f)
        if metadata:
            meta = yaml.load(metadata, Loader=yaml.FullLoader)
            meta.update(filename=name)
            return meta
