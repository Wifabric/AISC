"""Validate taggable Docker references without invoking a shell."""
import ipaddress
import re

_COMPONENT = r'[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*'
_DOMAIN = r'[A-Za-z0-9]+(?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9]+(?:[A-Za-z0-9-]*[A-Za-z0-9])?)*'

def valid_repository_tag(repository: str, tag: str) -> bool:
    if len(repository) > 255 or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}', tag):
        return False
    parts = repository.split('/')
    if len(parts) > 1 and ('.' in parts[0] or ':' in parts[0] or parts[0] == 'localhost' or any(c.isupper() for c in parts[0])):
        host = parts.pop(0)
        if host.startswith('['):
            match = re.fullmatch(r'\[([^]]+)\](?::[0-9]+)?', host)
            if not match: return False
            try: ipaddress.IPv6Address(match.group(1))
            except ValueError: return False
        elif not re.fullmatch(_DOMAIN + r'(?::[0-9]+)?', host):
            return False
    return bool(parts) and all(re.fullmatch(_COMPONENT, part) for part in parts)

def split_tagged_reference(reference: str) -> tuple[str, str]:
    repository, separator, tag = reference.rpartition(':')
    if not separator or not valid_repository_tag(repository, tag):
        raise ValueError('invalid image reference; expected repository:tag')
    return repository, tag

def canonical_tagged_reference(reference: str) -> str:
    repository, tag = split_tagged_reference(reference)
    first, separator, remainder = repository.partition('/')
    if not separator or not ('.' in first or ':' in first or first == 'localhost' or any(c.isupper() for c in first)):
        domain, path = 'docker.io', repository
    else:
        domain, path = first.lower(), remainder
    if domain == 'index.docker.io': domain = 'docker.io'
    if domain == 'docker.io' and '/' not in path: path = 'library/' + path
    return f'{domain}/{path}:{tag}'
