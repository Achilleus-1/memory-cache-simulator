import argparse
import math
from contextlib import redirect_stdout

PAGE_SIZE = 4096                # 4kb pages
TOTAL_PTE_ENTRIES = 512 * 1024  # 512k entries per process (fixed)

def process_access(page_table, address, length, free_obj, counters):
    """
    process memory access and update page table
    ignores kernel addresses (msb=1)
    """
    # ignore addresses in kernel space
    if address >= (1 << 31):
        return

    page = address // PAGE_SIZE
    if page in page_table:
        counters["page_hits"] += 1
    else:
        if free_obj["free"] > 0:
            page_table[page] = True
            counters["pages_from_free"] += 1
            free_obj["free"] -= 1
        else:
            counters["page_faults"] += 1

def process_trace_file(filename, free_obj, counters):
    """process a trace file and build page table for this process"""
    page_table = {}
    try:
        with open(filename, "r") as f:
            raw = f.readlines()
        lines = [line for line in raw if line.strip()]
    except Exception as e:
        print(f"error opening {filename}: {e}")
        return page_table

    i = 0
    while i < len(lines):
        # instruction fetch line
        line = lines[i].strip()
        if line.startswith("EIP"):
            try:
                sp = line.find("("); ep = line.find(")")
                instr_len = int(line[sp+1:ep])
                addr = int(line.split("):")[1].split()[0], 16)
                process_access(page_table, addr, instr_len, free_obj, counters)
            except:
                pass

        # data access line - check for both dst and src
        if i + 1 < len(lines) and "dstM:" in lines[i+1] and "srcM:" in lines[i+1]:
            d = lines[i+1].strip()
            
            # process destination address if valid
            try:
                dst_parts = d.split("dstM:")[1].split()[0:2]
                dst_addr = dst_parts[0]
                dst_data = dst_parts[1]
                
                # only process valid addresses with actual data
                if dst_addr != "00000000" and dst_data != "--------":
                    process_access(page_table, int(dst_addr, 16), 4, free_obj, counters)
            except:
                pass
                
            # process source address if valid
            try:
                src_parts = d.split("srcM:")[1].split()[0:2]
                src_addr = src_parts[0]
                src_data = src_parts[1]
                
                # only process valid addresses with actual data
                if src_addr != "00000000" and src_data != "--------":
                    process_access(page_table, int(src_addr, 16), 4, free_obj, counters)
            except:
                pass

        i += 2  # each instruction has two lines

    return page_table

def milestone1(args):
    # print header and input params
    print("Cache Simulator - CS 3853 – Team #12\n")
    print("Trace File(s):")
    for t in args.f: print(f"{t}")
    print()

    print("***** Cache Input Parameters *****\n")
    print(f"Cache Size:                     {args.s} KB")
    print(f"Block Size:                     {args.b} bytes")
    print(f"Associativity:                  {args.a}")
    rp = "Round Robin" if args.r.lower() == "rr" else "Random"
    print(f"Replacement Policy:             {rp}")
    print(f"Physical Memory:                {args.p} MB")
    print(f"Percent Memory Used by System:  {args.u:.1f}%")
    print("Instructions / Time Slice:      MAX" if args.n == -1 else f"Instructions / Time Slice:      {args.n}")

    # calculate cache geometry
    cache_bytes  = args.s * 1024
    total_blocks = cache_bytes // args.b
    total_rows   = total_blocks // args.a
    idx_bits     = int(math.log2(total_rows))
    off_bits     = int(math.log2(args.b))

    # calculate tag bits from physical address space
    phys_bits = int(math.log2(args.p * 1024 * 1024))
    tag_bits  = phys_bits - (idx_bits + off_bits)
    ov_bits   = tag_bits + 1  # +1 for valid bit
    overhead  = (total_blocks * ov_bits + 7) // 8  # bytes needed for overhead

    # calculate implementation size and cost
    impl_bytes = cache_bytes + overhead
    impl_kb    = impl_bytes / 1024
    cost       = impl_kb * 0.12  # $0.12 per KB

    print("\n***** Cache Calculated Values *****\n")
    print(f"Total # Blocks:                 {total_blocks}")
    print(f"Tag Size:                       {tag_bits} bits")
    print(f"Index Size:                     {idx_bits} bits")
    print(f"Total # Rows:                   {total_rows}")
    print(f"Overhead Size:                  {overhead} bytes")
    print(f"Implementation Memory Size:     {impl_kb:.2f} KB  ({impl_bytes} bytes)")
    print(f"Cost:                           ${cost:.2f} @ $0.12 per KB")

    # calculate physical memory parameters
    total_pp = (args.p * 1024 * 1024) // PAGE_SIZE  # total physical pages
    sys_pp   = int(total_pp * (args.u / 100.0))     # pages used by system

    # calculate page table size
    phys_page_bits = int(math.log2(total_pp))
    pte_bits       = 1 + phys_page_bits  # valid bit + physical page number
    total_pte_bits = TOTAL_PTE_ENTRIES * len(args.f) * pte_bits
    pte_ram_bytes  = total_pte_bits / 8  # convert bits to bytes

    print("\n***** Physical Memory Calculated Values *****\n")
    print(f"Number of Physical Pages:       {total_pp}")
    print(f"Number of Pages for System:     {sys_pp}")
    print(f"Size of Page Table Entry:       {pte_bits} bits  (1 valid bit, {phys_page_bits} for PhysPage)")
    print(f"Total RAM for Page Table(s):    {int(pte_ram_bytes)} bytes\n")

    return {
        "total_phys_pages": total_pp,
        "system_pages":     sys_pp,
        "pte_bits":         pte_bits
    }

def milestone2(args, total_pp, sys_pp, pte_bits):
    user_pp = total_pp - sys_pp  # pages available to user processes

    # set up counters for page table stats
    ctr = {"page_hits": 0, "pages_from_free": 0, "page_faults": 0}
    used_entries = []

    # one shared free pool for all processes
    free = {"free": user_pp}
    
    # process each trace file (each represents a process)
    for t in args.f:
        pt = process_trace_file(t, free, ctr)
        used_entries.append(len(pt))

    print("***** VIRTUAL MEMORY SIMULATION RESULTS *****\n")
    print(f"Physical Pages Used By SYSTEM:  {sys_pp}")
    print(f"Pages Available to User:        {user_pp}\n")
    
    mapped = ctr["page_hits"] + ctr["pages_from_free"]
    print(f"Virtual Pages Mapped:           {mapped}")
    print("------------------------------")
    print(f"Page Table Hits:                {ctr['page_hits']}")
    print(f"Pages from Free:                {ctr['pages_from_free']}")
    print(f"Total Page Faults:              {ctr['page_faults']}\n")

    print("Page Table Usage Per Process:")
    print("------------------------------")
    for i, (t, used) in enumerate(zip(args.f, used_entries)):
        wasted = int((TOTAL_PTE_ENTRIES - used) * (pte_bits / 8))
        pct    = used / TOTAL_PTE_ENTRIES * 100
        print(f"[{i}] {t}:")
        print(f"\tUsed Page Table Entries: {used}  ({pct:.2f}%)")
        print(f"\tPage Table Wasted: {wasted} bytes")

def main():
    # set up command line argument parser
    parser = argparse.ArgumentParser(
        description="vm & cache simulator - milestone #2: virtual memory simulation"
    )
    # define all required parameters
    parser.add_argument("-s", type=int, required=True,
                        help="cache size in kb (8 to 16384 kb)")
    parser.add_argument("-b", type=int, required=True,
                        help="block size in bytes (8, 16, 32, or 64)")
    parser.add_argument("-a", type=int, required=True,
                        help="associativity (1, 2, 4, 8, or 16)")
    parser.add_argument("-r", type=str, required=True, choices=["rr", "rnd", "RR", "RND"],
                        help="replacement policy: 'rr' or 'rnd'")
    parser.add_argument("-p", type=int, required=True,
                        help="physical memory in mb (128 to 4096 mb)")
    parser.add_argument("-u", type=float, required=True,
                        help="percent of physical memory used by os (0 to 100)")
    parser.add_argument("-n", type=int, required=True,
                        help="instructions/time slice (-1 for max)")
    parser.add_argument("-f", type=str, required=True, action="append",
                        help="trace file name (use multiple -f for up to 3 files)")
    
    args = parser.parse_args()
    
    # run the milestone calculations
    calculate_results = milestone1(args)
    milestone2(args, calculate_results["total_phys_pages"], calculate_results["system_pages"], calculate_results["pte_bits"])

if __name__ == "__main__":
    # redirect stdout to output file
    with open("Team_12_Sim_n_M#2.txt","w") as out:
        with redirect_stdout(out):
            main()