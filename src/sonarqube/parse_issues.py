from pathlib import Path
from sys import path as sys_path
from typing import Any, Dict, List, Optional, TypedDict
from requests import get as requests_get
from json import dump as json_dumps

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys_path:
    sys_path.insert(0, str(REPO_ROOT))

from src.settings import settings  # noqa: E402

DEFAULT_SEVERITIES = 'BLOCKER,CRITICAL,MAJOR,MINOR'
DEFAULT_TYPES = 'CODE_SMELL,BUG,VULNERABILITY'


class SonarQubeIssue(TypedDict):
    rule_key: str
    severity: str
    file_path: str
    line: int
    debt_minutes: int
    message: str


def parse_sonarqube_debt_string(debt_str: Optional[str]) -> int:
    if not debt_str:
        return 0
    total = 0
    if 'h' in debt_str:
        parts = debt_str.split('h')
        total += int(parts[0]) * 60
        debt_str = parts[1]
    if 'min' in debt_str:
        total += int(debt_str.replace('min', '').strip())
    return total


def _fetch_all_pages(
    base_url: str, auth: tuple, params: dict
) -> List[Dict[str, Any]]:
    issues = []
    page = 1
    while True:
        response = requests_get(
            f'{base_url}/api/issues/search',
            auth=auth,
            params={**params, 'p': page, 'ps': 500},
        )
        response.raise_for_status()
        data = response.json()

        if not data['issues']:
            break

        issues.extend(data['issues'])
        page += 1

    return issues


def write_sonarqube_issues_to_disk(
    severities: str = DEFAULT_SEVERITIES,
    types: str = DEFAULT_TYPES,
    output_path: Path = Path.cwd() / 'sonarqube_issues.json',
) -> None:
    raw_issues = _fetch_all_pages(
        base_url=settings.sq_url,
        auth=(settings.sq_token, ''),
        params={
            'componentKeys': settings.sq_project_key,
            'types': types,
            'severities': severities,
        },
    )

    issues: List[SonarQubeIssue] = []
    for raw_issue in raw_issues:
        line_number = raw_issue.get('line')
        if not line_number:
            continue  # Without a target line, we can't say to the LLM
            # where the issue is.

        issue = SonarQubeIssue(
            rule_key=raw_issue.get('rule', ''),
            severity=raw_issue.get('severity', ''),
            file_path=raw_issue.get('component', ''),
            line=line_number,
            debt_minutes=parse_sonarqube_debt_string(raw_issue.get('debt')),
            message=raw_issue.get('message', ''),
        )
        issues.append(issue)

    with open(output_path, 'w') as f:
        json_dumps(issues, f, indent=4)


if __name__ == '__main__':
    write_sonarqube_issues_to_disk()
