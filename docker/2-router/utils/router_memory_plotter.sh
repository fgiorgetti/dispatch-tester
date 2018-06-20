#!/bin/bash
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

qdstats_path="results"
out_path="${qdstats_path}/router_memory_plotter"

#
# Processes all provided router files based on given router id.
# If given router id is: 'router1' then all files matching:
# /tmp/router1.[0-9]* will be processed (considering tmp is qdstats_path).
#
process_router() {

    # Parse router files prefix
    router_id="$1"
	file_list="${qdstats_path}/$1.[0-9]*"
    echo "Processing ${router_id} files: /${qdstats_path}/$1.[0-9]*"

	# Load all metrics found
	first_data_file=`ls -1 ${file_list}|head -1`
	metrics=()
	for metric in `tail -n+4 $first_data_file | awk '{print $1}'`; do
	    metrics+=("$metric")
	done
	
	# For each file
	for m in "${metrics[@]}"; do
	    file="${out_path}/${m}.${router_id}.data"
	    rm "${file}" 2> /dev/null
	    echo "Saving: $file"
	    printf "# Metric: %s\n" $m >> ${file}
	    printf "# %-10s %-10s %-10s\n" "Length" "Total" "In-Threads" >> ${file}
	    for f in `ls -1 ${file_list} | sort -t'.' -k2n`; do
	        length=`echo "${f}" | awk -F'.' '{print $2}'`
	        egrep "^[ ]*${m}" $f | sed -e 's/,//g' | awk -v msglen="$length" '{printf "%-10d %-10d %-10d\n", msglen, $5, $6}' >> ${file}
	    done
	done
	
	echo All files saved at ${out_path}
	
	if [[ -z `which gnuplot 2> /dev/null` ]]; then
	    echo Gnuplot not installed, unable to generate charts
	    exit 0
	fi
	
	echo "Generating charts (png)"
	for m in "${metrics[@]}"; do
	    data_file="${out_path}/${m}.${router_id}.data"
	    img_file="${out_path}/${m}.${router_id}.data.png"
	    echo "Saving image: ${img_file}"
	    cat << EOF | gnuplot 2> /dev/null
	    set title "$m"
	    set xtics auto
	    set ytics auto
	    set term png
	    set output "$img_file"
	    plot "$data_file" using 1:2 title 'Total' with linespoints, \
	    "$data_file" using 1:3 title 'In-Threads' with linespoints
EOF
	done

}

# Create the output path
mkdir ${out_path} 2> /dev/null || true
[[ ! -d ${out_path} || ! -w ${out_path} ]] && \
    echo "Output path invalid or not writeable" && \
    exit 1

# Loop through each router files
router_files=('router1' 'router2')
for router_file in ${router_files[@]}; do
    process_router "$router_file"
done

