def strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s

def describe_string_list(strings: list[str], last_delimiter: str) -> str:
    if not strings:
        return ""
    if len(strings) == 1:
        return strings[0]
    return f"{', '.join(strings[:-1])} {last_delimiter} {strings[-1]}"

def add_to_list(l: list[str], items: list[str]):
    for i in items:
        if i not in l:
            l.append(i)

def remove_from_list(l: list[str], items: list[str]):
    for i in items:
        if i in l:
            l.remove(i)
