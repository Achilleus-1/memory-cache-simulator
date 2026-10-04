import argparse
import math
import random
from contextlib import redirect_stdout

PAGE_SIZE = 4096                # 4kb pages
TOTAL_PTE_ENTRIES = 512 * 1024  # 512k entries per process (fixed)

class CacheLine:
    """represents a single cache line with tag and valid bit"""
    def __init__(self):
        self.valid = False
        self.tag = 0
        self.last_used = 0  # for replacement policy

class Cache:
    """represents the entire cache structure"""
    def __init__(self, cache_size_kb, block_size, associativity, replacement_policy):
        # cache parameters
        self.cache_size = cache_size_kb * 1024  # bytes
        self.block_size = block_size  # bytes per block
        self.associativity = associativity
        self.replacement_policy = replacement_policy.lower()
        
        # calculate cache geometry
        self.total_blocks = self.cache_size // self.block_size
        self.total_sets = self.total_blocks // self.associativity
        
        # calculate bit sizes
        self.offset_bits = int(math.log2(self.block_size))
        self.index_bits = int(math.log2(self.total_sets))
        self.tag_bits = 32 - self.index_bits - self.offset_bits
        
        # calculate overhead
        self.overhead_bits_per_block = self.tag_bits + 1  # tag + valid bit
        self.overhead_bytes = (self.total_blocks * self.overhead_bits_per_block + 7) // 8
        
        # init cache structure - list of sets, each set is a list of cache lines
        self.sets = []
        for i in range(self.total_sets):
            set_lines = []
            for j in range(self.associativity):
                line = CacheLine()
                set_lines.append(line)
            self.sets.append(set_lines)
        
        # tracking stats
        self.accesses = 0
        self.hits = 0
        self.compulsory_misses = 0
        self.conflict_misses = 0
        self.instruction_bytes = 0
        self.src_dst_bytes = 0
        self.cycles = 0
        self.instruction_count = 0
        
        # counters for rr replacement policy - one per set
        self.rr_counters = [0] * self.total_sets
        
    def get_address_parts(self, address):
        """break an address into tag, index, offset"""
        offset = address & ((1 << self.offset_bits) - 1)
        index = (address >> self.offset_bits) & ((1 << self.index_bits) - 1)
        tag = address >> (self.offset_bits + self.index_bits)
        return tag, index, offset
    
    def access(self, address, length, is_instruction):
        """access the cache at address for a certain length; returns cycles used"""
        # track instruction or data bytes
        if is_instruction:
            self.instruction_bytes += length
            self.instruction_count += 1
        else:
            self.src_dst_bytes += length
        
        # determine which blocks this access spans
        start_address = address
        end_address = address + length - 1
        start_block = start_address // self.block_size
        end_block = end_address // self.block_size
        
        total_cycles = 0
        
        # access each block
        for block_num in range(start_block, end_block + 1):
            block_addr = block_num * self.block_size
            tag, index, _ = self.get_address_parts(block_addr)
            
            # increment access counter
            self.accesses += 1
            
            # check if hit
            hit = False
            hit_way = -1
            
            for way, line in enumerate(self.sets[index]):
                if line.valid and line.tag == tag:
                    hit = True
                    hit_way = way
                    self.hits += 1
                    total_cycles += 1  # cache hit costs 1 cycle
                    break
            
            # if miss, handle it
            if not hit:
                # handle replacement
                replace_way = self.choose_replacement(index)
                
                # check if this is compulsory or conflict miss
                if not self.sets[index][replace_way].valid:
                    self.compulsory_misses += 1
                else:
                    self.conflict_misses += 1
                
                # update cache line
                self.sets[index][replace_way].valid = True
                self.sets[index][replace_way].tag = tag
                
                # calculate miss penalty
                # memory reads needed = ceil(block_size / 4) (4 bytes per read)
                mem_reads = math.ceil(self.block_size / 4)  # using math.ceil to match professor's implementation
                mem_cycles = mem_reads * 4  # 4 cycles per memory read
                total_cycles += mem_cycles
        
        # add instruction execution or effective address calculation cost
        if is_instruction:
            total_cycles += 2  # instruction execution
        else:
            total_cycles += 1  # effective address calculation
            
        # accumulate cycles
        self.cycles += total_cycles
        
        return total_cycles
    
    def choose_replacement(self, index):
        """Choose which way to replace in the given set"""
        # first check for any invalid (empty) lines - use these first
        for way, line in enumerate(self.sets[index]):
            if not line.valid:
                return way
        
        # if all lines are valid, apply replacement policy
        if self.replacement_policy == "rr":
            # for round robin, just go through ways in order
            way = self.rr_counters[index]
            # update counter for next time
            self.rr_counters[index] = (self.rr_counters[index] + 1) % self.associativity
            return way
        else:
            # random replacement
            # use consistent seed for reproducible results
            return random.randint(0, self.associativity - 1)

def process_access(page_table, address, length, free_obj, counters, cache=None, is_instruction=False):
    """
    process memory access and update page table
    ignores kernel addresses (msb=1)
    """
    # ignore addresses in kernel space
    if address >= (1 << 31):
        return 0
    
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
            # add 100 cycles penalty for each page fault
            if cache is not None:
                cache.cycles += 100
    
    # if cache simulation is active, access the cache
    cycles = 0
    if cache is not None:
        cycles = cache.access(address, length, is_instruction)
    
    return cycles

def process_trace_file(filename, free_obj, counters, cache=None):
    """Process a trace file and build page table for this process"""
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
                # parse instruction length and address
                sp = line.find("("); ep = line.find(")")
                instr_len = int(line[sp+1:ep])
                addr = int(line.split("):")[1].split()[0], 16)
                process_access(page_table, addr, instr_len, free_obj, counters, cache, is_instruction=True)
            except Exception as e:
                pass

        # data access line - check for both dst and src
        if i + 1 < len(lines) and "dstM:" in lines[i+1] and "srcM:" in lines[i+1]:
            d = lines[i+1].strip()
            
            # process destination address if valid
            try:
                dst_parts = d.split("dstM:")[1].split()[0:2]
                dst_addr = dst_parts[0]
                dst_data = dst_parts[1] if len(dst_parts) > 1 else "--------"
                
                # only process valid addresses with actual data
                if dst_addr != "00000000" and dst_data != "--------":
                    process_access(page_table, int(dst_addr, 16), 4, free_obj, counters, cache, is_instruction=False)
            except Exception as e:
                pass
                
            # process source address if valid
            try:
                src_parts = d.split("srcM:")[1].split()[0:2]
                src_addr = src_parts[0]
                src_data = src_parts[1] if len(src_parts) > 1 else "--------"
                
                # only process valid addresses with actual data
                if src_addr != "00000000" and src_data != "--------":
                    process_access(page_table, int(src_addr, 16), 4, free_obj, counters, cache, is_instruction=False)
            except Exception as e:
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
        "pte_bits":         pte_bits,
        "impl_kb":          impl_kb,
        "total_blocks":     total_blocks,
        "overhead_size":    overhead
    }

def milestone2(args, calc_results, cache=None):
    user_pp = calc_results["total_phys_pages"] - calc_results["system_pages"]  # pages available to user processes

    # set up counters for page table stats
    ctr = {"page_hits": 0, "pages_from_free": 0, "page_faults": 0}
    used_entries = []

    # one shared free pool for all processes
    free = {"free": user_pp}
    
    # process each trace file (each represents a process)
    for t in args.f:
        pt = process_trace_file(t, free, ctr, cache)
        used_entries.append(len(pt))

    print("***** VIRTUAL MEMORY SIMULATION RESULTS *****\n")
    print(f"Physical Pages Used By SYSTEM:  {calc_results['system_pages']}")
    print(f"Pages Available to User:        {user_pp}")
    
    mapped = ctr["page_hits"] + ctr["pages_from_free"]
    print(f"Virtual Pages Mapped:           {mapped}")
    print("------------------------------")
    print(f"Page Table Hits:                {ctr['page_hits']}")
    print(f"Pages from Free:                {ctr['pages_from_free']}")
    print(f"Total Page Faults:              {ctr['page_faults']}\n")

    print("Page Table Usage Per Process:")
    print("------------------------------")
    for i, (t, used) in enumerate(zip(args.f, used_entries)):
        wasted = int((TOTAL_PTE_ENTRIES - used) * (calc_results["pte_bits"] / 8))
        pct    = used / TOTAL_PTE_ENTRIES * 100
        print(f"[{i}] {t}:")
        print(f"\tUsed Page Table Entries: {used}  ({pct:.2f}%)")
        print(f"\tPage Table Wasted: {wasted} bytes")
    
    return mapped

def milestone3(args, calc_results, cache, addr_count):
    """calculate and display cache simulation results"""
    misses = cache.compulsory_misses + cache.conflict_misses
    
    # calculate hit rate and miss rate
    hit_rate = (cache.hits * 100) / cache.accesses if cache.accesses > 0 else 0
    miss_rate = 100 - hit_rate
    
    # calculate cpi
    cpi = cache.cycles / cache.instruction_count if cache.instruction_count > 0 else 0
    
    # calculate unused cache space based on compulsory misses only
    used_blocks = cache.compulsory_misses
    unused_blocks = calc_results["total_blocks"] - used_blocks
    
    # calculate overhead per block
    overhead_per_block = calc_results["overhead_size"] / calc_results["total_blocks"]
    
    # calculate unused kb using professor's formula
    unused_kb = (unused_blocks * (args.b + overhead_per_block)) / 1024
    
    # calculate waste
    waste = unused_kb * 0.12
    
    # calculate unused percentage
    unused_pct = (unused_kb / calc_results["impl_kb"]) * 100
    
    print("\nMILESTONE #3: - Cache Simulation Results\n")
    print("***** CACHE SIMULATION RESULTS *****\n")
    print(f"Total Cache Accesses:           {cache.accesses} ({addr_count} addresses)")
    print(f"--- Instruction Bytes:          {cache.instruction_bytes}")
    print(f"--- SrcDst Bytes:               {cache.src_dst_bytes}")
    print(f"Cache Hits:                     {cache.hits}")
    print(f"Cache Misses:                   {misses}")
    print(f"--- Compulsory Misses:          {cache.compulsory_misses}")
    print(f"--- Conflict Misses:            {cache.conflict_misses}")
    
    print("\n***** *****  CACHE HIT & MISS RATE:  ***** *****\n")
    print(f"Hit  Rate:                      {hit_rate:.4f}%")
    print(f"Miss Rate:                      {miss_rate:.4f}%")
    print(f"CPI:                            {cpi:.2f} Cycles/Instruction  ({cache.cycles})")
    print(f"Unused Cache Space:             {unused_kb:.2f} KB / {calc_results['impl_kb']:.2f} KB = {unused_pct:.2f}%  Waste: $ {waste:.2f}")
    print(f"Unused Cache Blocks:            {unused_blocks} / {calc_results['total_blocks']}")

def main():
    # set up command line argument parser
    parser = argparse.ArgumentParser(
        description="vm & cache simulator - milestone #3: cache simulation"
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
    
    # use a fixed seed for random replacement policy for reproducible results
    random.seed(42)
    
    # create the cache
    cache = Cache(args.s, args.b, args.a, args.r)
    
    # run all milestone calculations
    calc_results = milestone1(args)
    addr_count = milestone2(args, calc_results, cache)
    milestone3(args, calc_results, cache, addr_count)

if __name__ == "__main__":
    # redirect stdout to output file
    with open("Team_12_Sim_n_M#3.txt","w") as out:
        with redirect_stdout(out):
            main()