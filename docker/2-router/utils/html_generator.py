import argparse
import os
import re
import os
from jinja2 import Template
from collections import OrderedDict


parser = argparse.ArgumentParser(description='HTML Generator')
parser.add_argument('-r', '--result-dir', action='append', required=True, help="Result directory containing PNG images")
parser.add_argument('-l', '--label', action='append', required=True, help="Label to identify each result directory")
args = parser.parse_args()

# Ensure numbers of labels and directories are equals
assert len(args.result_dir) == len(args.label), 'Number of directories and labels must be a match'

# Constants
IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480
TOTAL_WIDTH = 90  # percentage left for charts
CUR_DIR = os.path.dirname(os.path.realpath(__file__))

#
# Allocators data
#
# Read files and identify all allocators found
allocator_dict = {}
allocator_regex = re.compile(r'\.router[12]\.data\.png')

# Populating all allocators found first
for dir in args.result_dir:
    # Only consider PNG files
    files = [f for f in os.listdir(dir) if f.lower().endswith('.png')]

    # If none found, ignore it
    if not files:
        continue

    # Strip allocator name from filename
    files.sort()
    uniq_file_list = list(set([allocator_regex.sub('',fn) for fn in files]))
    uniq_file_list.sort()

    for allocator_name in uniq_file_list:
        if allocator_name in allocator_dict:
            allocator = allocator_dict[allocator_name]
        else:
            allocator = {
                'name': allocator_name,
                'results': []
            }
            allocator_dict[allocator_name] = allocator

# Now loop through all allocators and add images related with each specific directory
# or add a blank image if none exists
for allocator_name in allocator_dict.keys():
    allocator = allocator_dict[allocator_name]
    for dir in args.result_dir:
        router1_image = '%s/%s.router1.data.png' % (dir, allocator_name)
        router2_image = '%s/%s.router2.data.png' % (dir, allocator_name)

        # Appending images from given result dir to allocator
        allocator['results'].append({'router1_image': router1_image,
                                     'router2_image': router2_image})

# Sorted allocator dictionary
sorted_allocator_dict = OrderedDict(sorted(allocator_dict.items(), key=lambda t: t[0]))

# Rendering dictionary
render_dict = {
    'labels': args.label,
    'column_width': '%d%%' % int(TOTAL_WIDTH / len(args.label)),
    'image_width': IMAGE_WIDTH / len(args.label),
    'image_height': IMAGE_HEIGHT / len(args.label),
    'allocators': sorted_allocator_dict.values()
}

# Loading and rendering the template
with open('%s/html_template.j2' % CUR_DIR) as template_file:
    template = Template(template_file.read())

print(template.render(**render_dict))
# print(render_dict)
