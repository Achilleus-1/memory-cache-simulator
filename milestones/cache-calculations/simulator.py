import argparse
import math
from contextlib import redirect_stdout

def main():
    parser = argparse.ArgumentParser(
        description="Cache Simulator - CS 3853 – Milestone #1: Input Parameters and Calculated Values"
    )
    # specify input parameters via argparser from project specifications
    parser.add_argument("-s", type=int, required=True,
                        help="Cache size in KB (8 to 16384 KB)")
    parser.add_argument("-b", type=int, required=True,
                        help="Block size in bytes (8, 16, 32, or 64)")
    parser.add_argument("-a", type=int, required=True,
                        help="Associativity (1, 2, 4, 8, or 16)")
    parser.add_argument("-r", type=str, required=True, choices=["rr", "rnd", "RR", "RND"],
                        help="Replacement policy: 'RR' (Round Robin) or 'RND' (Random)")
    parser.add_argument("-p", type=int, required=True,
                        help="Physical memory in MB (128 to 4096 MB)")
    parser.add_argument("-u", type=float, required=True,
                        help="Percent of physical memory used by OS (0 to 100)")
    parser.add_argument("-n", type=int, required=True,
                        help="Instructions/Time Slice (enter -1 for max)")
    parser.add_argument("-f", type=str, required=True, action="append",
                        help="Trace file name (specify multiple -f for up to 3 trace files)")
    
    args = parser.parse_args()
    
    # print project and team information
    print("Cache Simulator - CS 3853 – Team #12\n")
    
    # print trace files
    print("Trace File(s):")
    for trace in args.f:
        print(f"\t{trace}")
    print()

    # print cache input args
    print("***** Cache Input Parameters *****\n")
    print(f"Cache Size:                     {args.s} KB")
    print(f"Block Size:                     {args.b} bytes")
    print(f"Associativity:                  {args.a}")

    # determine replacement policy vals
    rep_policy = "Round Robin" if args.r.lower() == "rr" else "Random"
    print(f"Replacement Policy:             {rep_policy}")

    print(f"Physical Memory:                {args.p} MB")
    print(f"Percent Memory Used by System:  {args.u:.1f}%")
    if args.n == -1:
        print("Instructions / Time Slice:      MAX")
    else:
        print(f"Instructions / Time Slice:      {args.n}")

    ## cache conversions below

    cache_size_bytes = args.s * 1024  # Convert KB to bytes
    total_blocks = cache_size_bytes // args.b
    total_rows = total_blocks // args.a
    index_size = int(math.log2(total_rows))
    block_offset = int(math.log2(args.b))

    effective_address_bits = 27
    tag_size = effective_address_bits - (index_size + block_offset)
    
    # each block will store its single tag plus a single valid bit
    overhead_bits_per_block = tag_size + 1
    overhead_total_bytes = (total_blocks * overhead_bits_per_block + 7) // 8
    
    implementation_memory_bytes = cache_size_bytes + overhead_total_bytes
    implementation_memory_kb = implementation_memory_bytes / 1024
    cost = implementation_memory_kb * 0.12  # Cost per KB
    
    print("\n***** Cache Calculated Values *****\n")
    print(f"Total # Blocks:                 {total_blocks}")
    print(f"Tag Size:                       {tag_size} bits")
    print(f"Index Size:                     {index_size} bits")
    print(f"Total # Rows:                   {total_rows}")
    print(f"Overhead Size:                  {overhead_total_bytes} bytes")
    print(f"Implementation Memory Size:     {implementation_memory_kb:.2f} KB  ({implementation_memory_bytes} bytes)")
    print(f"Cost:                           ${cost:.2f} @ $0.12 per KB")


    ## physical memory calculations

    # page size is 4096 bytes -- (4KB)
    page_size = 4096
    total_phys_pages = (args.p * 1024 * 1024) // page_size
    system_pages = int(total_phys_pages * (args.u / 100.0))
    page_table_entry_size_bits = 16  # 1 valid bit && 15 bits for physical page number

    fixed_page_table_entries = 512 * 1024  # 512K entries per process
    # total RAM for page tables -- fixed entries * number of trace files * entry size (in bytes)
    total_page_table_ram = fixed_page_table_entries * len(args.f) * (page_table_entry_size_bits // 8)

    print("\n***** Physical Memory Calculated Values *****\n")
    print(f"Number of Physical Pages:       {total_phys_pages}")
    print(f"Number of Pages for System:     {system_pages}")
    print(f"Size of Page Table Entry:       {page_table_entry_size_bits} bits")
    print(f"Total RAM for Page Table(s):    {total_page_table_ram} bytes")
    
if __name__ == "__main__":
    # redirect output to txt file
    with open("Team_12_Sim_n_M#1.txt", "w") as outfile:
        with redirect_stdout(outfile):
            main()
