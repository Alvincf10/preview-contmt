"""Share identical AVR instruction runs in GCC's final LTO assembly.

CALL and RET preserve registers and SREG. A shared run may use the original
frame pointer but must not push, pop, or use stack-passed arguments. Runs ending
in an unconditional exit can also share stack operations because they use JMP.
The linker relaxes both transfers when a relative instruction can reach.
"""

from collections import defaultdict
from dataclasses import dataclass
import re


DATA_OPERATIONS = frozenset("""
    mov movw ld ldd ldi st std lpm clr andi and or ori add adc adiw sub subi
    sbc sbci sbiw eor lsl lsr ror inc dec com neg cpi cp cpc tst swap mul
    muls mulsu clc sec
""".split())
SKIP_OPERATIONS = frozenset(("cpse", "sbrs", "sbrc", "sbis", "sbic"))
STACK_OPERATIONS = frozenset(("pop", "push"))
WIDE_OPERATIONS = frozenset(("call", "jmp", "lds", "sts"))
EXITS = frozenset(("ret", "jmp", "rjmp", "ijmp", "eijmp"))
REGISTER_CALLS = frozenset("""
    __addsf3 __subsf3 __mulsf3 __divsf3 __floatsisf __floatunsisf __fixsfsi
    __fp_cmp __mulsi3 __udivmodsi4 __divmodsi4 __cmpsf2 __fixunssfsi __lesf2
    __gesf2 logf log memcpy memset
""".split())
PANEL_CALLS = ("3sepEv", "6digits", "4real", "6scaled", "9timestamp", "4endEv", "5flash")
JOURNAL_CALLS = ("4load", "5begin", "3get", "4peek", "4scan", "4push", "6append")
SHAREABLE_FUNCTIONS = (
    "_ZN5conmt7Journal", "_ZN5conmt6Engine", "_ZN5conmt5panel",
    "_ZN5conmt8Integral", "_ZN5conmt10Regression",
    "_ZN5conmt6number", "_ZN5conmt7integer", "_ZN5conmt4date", "_ZN5conmt5clock",
    "_ZN5conmt5board12_GLOBAL__N_1L8volumeAt", "_ZN5conmt5board12_GLOBAL__N_1L11nextCluster",
    "_ZN5conmt5board5mount", "_ZN5conmt5board12_GLOBAL__N_1L4load", ".Lconmt_share",
)
FUNCTION = re.compile(r"\.type\s+(\S+),\s*@function$")
FUNCTION_END = re.compile(r"\.size\s+(\S+),")
RELATIVE_OPERAND = re.compile(r"\b[0-9]+[fb]\b|(?<![\w.$])\.(?![\w.$])")


@dataclass(frozen=True)
class Instruction:
    line: int
    function: str
    block: int
    address: int
    words: int
    text: str
    stack: bool
    terminal: bool


@dataclass(frozen=True)
class Occurrence:
    start: int
    end: int
    words: int
    terminal: bool


def register_call(target):
    return (target in REGISTER_CALLS or target.startswith(".Lconmt_share") or
            (target.startswith("_ZN5conmt5panel") and any(tag in target for tag in PANEL_CALLS)) or
            (target.startswith("_ZN5conmt7Journal") and any(tag in target for tag in JOURNAL_CALLS)))


def scan(lines):
    instructions = []
    anchors = {}
    block = address = 0
    function = last = ""
    for index, line in enumerate(lines):
        command = line.split(";", 1)[0].strip()
        if match := FUNCTION.match(command):
            function, last = match[1], ""
        if (match := FUNCTION_END.match(command)) and match[1] == function:
            if last in EXITS:
                anchors[function] = (index, address)
            function = ""
        if not command or command.startswith(("#", "/*", "*", "*/")):
            continue
        if command.endswith(":") or command.startswith("."):
            block += 1
            continue
        if not function:
            continue
        op, *args = command.split(None, 1)
        operand = args[0] if args else ""
        words = 2 if op in WIDE_OPERATIONS else 1
        terminal = op == "ret" or (op == "jmp" and not operand.startswith("."))
        stack = op in STACK_OPERATIONS
        allowed = (terminal or stack or op in DATA_OPERATIONS or
                   (op in ("lds", "sts") and "_ZN" in operand) or
                   (op == "call" and register_call(operand)))
        if (allowed and function.startswith(SHAREABLE_FUNCTIONS) and last not in SKIP_OPERATIONS
                and not RELATIVE_OPERAND.search(operand)):
            instructions.append(Instruction(index, function, block, address, words,
                                            op + " " + operand, stack, terminal))
            if terminal:
                block += 1
        else:
            block += 1
        last = op
        address += words
    return instructions, anchors


def find_runs(instructions):
    groups = defaultdict(list)
    for start, first in enumerate(instructions):
        signature = []
        words = 0
        stack = False
        for end in range(start, min(start + 24, len(instructions))):
            item = instructions[end]
            if item.block != first.block:
                break
            signature.append(item.text)
            words += item.words
            stack |= item.stack
            if words >= 3 and (not stack or item.terminal):
                groups[tuple(signature)].append(Occurrence(start, end + 1, words, item.terminal))
            if item.terminal:
                break
    return groups.values()


def estimate(group):
    first = group[0]
    return (len(group) - 1) * first.words - len(group) - (not first.terminal)


def outline(assembly, pass_number):
    lines = assembly.splitlines()
    instructions, anchors = scan(lines)
    groups = sorted((group for group in find_runs(instructions) if len(group) > 1),
                    key=estimate, reverse=True)
    used = set()
    insertions = defaultdict(list)
    replacements = {}
    omitted = set()
    count = 0
    for group in groups:
        sites = []
        for candidate in group:
            if ((not sites or candidate.start >= sites[-1].end) and
                    used.isdisjoint(range(candidate.start, candidate.end))):
                sites.append(candidate)
        if len(sites) < 2:
            continue
        functions = sorted({instructions[site.start].function for site in sites} & anchors.keys())
        if not functions:
            continue
        addresses = [instructions[site.start].address for site in sites]
        first = sites[0]

        def nearby(function):
            return sum(abs(anchors[function][1] - address) < 2040 for address in addresses)

        anchor = max(functions, key=nearby)
        gain = len(sites) * (first.words - 2) + nearby(anchor) - first.words - (not first.terminal)
        if gain <= 0:
            continue
        label = f".Lconmt_share_{pass_number}_{count}"
        snippet = [f"\t.type\t{label}, @function", f"{label}:"]
        snippet.extend(lines[instructions[i].line] for i in range(first.start, first.end))
        if not first.terminal:
            snippet.append("\tret")
        snippet.append(f"\t.size\t{label}, .-{label}")
        insertions[anchors[anchor][0]].extend(snippet)
        transfer = "jmp" if first.terminal else "call"
        for site in sites:
            used.update(range(site.start, site.end))
            replacements[instructions[site.start].line] = f"\t{transfer}\t{label}"
            omitted.update(instructions[i].line for i in range(site.start + 1, site.end))
        count += 1
    if not count:
        return assembly, count
    output = []
    for i, line in enumerate(lines):
        if i not in omitted:
            output.append(replacements.get(i, line))
        output.extend(insertions.get(i, ()))
    return "\n".join(output) + "\n", count
