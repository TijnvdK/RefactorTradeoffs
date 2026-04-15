import xml.etree.ElementTree as ET
from csv import DictReader as csv_dict_reader
from csv import DictWriter as csv_dict_writer
from html import unescape as html_unescape
from pathlib import Path
from typing import Dict, List, Literal, TypedDict

### Types ###


class PDependOutput(TypedDict):
    file_path: str
    method_name: str
    start_line: int
    end_line: int
    cc: float
    mi: float
    halstead_difficulty: float


class PHPCSOutput(TypedDict):
    line: int
    type: Literal['error', 'warning']


class PHPMDOutput(TypedDict):
    line: int
    rule: str
    message: str


class PHPMetricsOutput(TypedDict):
    halstead_difficulty: float
    mi: float
    cc: float


class PDependWithPHPMD(PDependOutput):
    phpmd_violations: List[PHPMDOutput]


### Parsers ###


def parse_pdepend(path: str) -> List[PDependOutput]:
    """
    Retrieve the per-method metrics CC, MI, and Halstead difficulty
    from an pdepend XML file.

    **Important**: The file doesn't validate the structure of the given XML
    file; it is up to the user to make sure that the file structure is correct.
    If the structure is not adhered to, the output will be empty.

    Args:
        path (str): The path to the pdepend.xml file.

    Returns:
        List[PDependOutput]: The parsed output.
    """
    xml_tree = ET.parse(path)

    result: List[PDependOutput] = []

    root = xml_tree.getroot()
    for package in root.iter('package'):
        for class_ in package.iter('class'):
            file_element = class_.find('file')

            if file_element is not None:
                file_path = file_element.get('name', 'Unknown')
            else:
                file_path = 'Unknown'

            for method in class_.findall('method'):
                result.append(
                    PDependOutput(
                        file_path=file_path,
                        method_name=method.get('name', 'Unknown'),
                        start_line=int(method.get('start', '0')),
                        end_line=int(method.get('end', '0')),
                        cc=float(method.get('ccn', '0')),
                        mi=float(method.get('mi', '0')),
                        halstead_difficulty=float(method.get('hd', '0')),
                    )
                )

    return result


def parse_phpcs(path: str) -> Dict[str, List[PHPCSOutput]]:
    """
    Retrieve style violations on line-level.

    **Important**: The file doesn't validate the structure of the given XML
    file; it is up to the user to make sure that the file structure is correct.
    If the structure is not adhered to, the output will be empty.

    Args:
        path (str): The path to the phpcs.xml file.

    Returns:
        List[PHPCSOutput]: The parsed output.
    """
    xml_tree = ET.parse(path)

    result: Dict[str, List[PHPCSOutput]] = {}

    root = xml_tree.getroot()
    for file_ in root.findall('file'):
        file_path = file_.get('name', 'Unknown')

        result[file_path] = []

        for error_ in file_.findall('error'):
            result[file_path].append(
                PHPCSOutput(
                    line=int(error_.get('line', '0')),
                    type='error',
                )
            )
        for warning_ in file_.findall('warning'):
            result[file_path].append(
                PHPCSOutput(
                    line=int(warning_.get('line', '0')),
                    type='warning',
                )
            )

    return result


def parse_phpmd(path: str) -> Dict[str, List[PHPMDOutput]]:
    """
    Retrieve code smells on line-level.

    **Important**: The file doesn't validate the structure of the given XML
    file; it is up to the user to make sure that the file structure is correct.
    If the structure is not adhered to, the output will be empty.

    Args:
        path (str): The path to the phpmd.xml file.

    Returns:
        List[PHPMDOutput]: The parsed output.
    """
    xml_tree = ET.parse(path)

    result: Dict[str, List[PHPMDOutput]] = {}

    root = xml_tree.getroot()
    for file_ in root.findall('file'):
        file_path = file_.get('name', 'Unknown')

        result[file_path] = []

        for violation in file_.findall('violation'):
            text = (
                html_unescape(violation.text.strip()) if violation.text else ''
            )
            result[file_path].append(
                PHPMDOutput(
                    file_path=file_path,
                    line=int(violation.get('beginline', '0')),
                    rule=violation.get('rule', 'Unknown'),
                    message=text,
                )
            )

    return result


def parse_phpmetrics(path: str) -> Dict[str, PHPMetricsOutput]:
    """
    Retrieve the per-class metrics CC, MI, and Halstead difficulty
    from an phpmetrics CSV file.

    **Important**: The file doesn't validate the structure of the given CSV
    file; it is up to the user to make sure that the file structure is correct.
    If the structure is not adhered to, the output will be empty.

    Args:
        path (str): The path to the phpmetrics.csv file.

    Returns:
        Dict[str, PHPMetricsOutput]: The parsed output.
    """
    result: Dict[str, PHPMetricsOutput] = {}

    with open(path, newline='', encoding='utf-8') as file_:
        reader = csv_dict_reader(file_)
        for row in reader:
            name = row.get('name', '').strip('"')
            try:
                result[name] = PHPMetricsOutput(
                    halstead_difficulty=float(row.get('difficulty', 0) or 0),
                    mi=float(row.get('mi', 0) or 0),
                    cc=float(row.get('ccn', 0) or 0),
                )
            except (TypeError, ValueError):
                continue

    return result


### Caller ###


def _append_side_phpmd_to_base(
    base: List[PDependOutput], side_phpmd: Dict[str, List[PHPMDOutput]]
) -> List[PDependWithPHPMD]:
    """
    Combines PDependOutput with PHPMDOutput by matching file paths and
    line numbers.

    Args:
        base (List[PDependOutput]): The base PDepend output to which
            PHPMD violations will be appended.
        side_phpmd (Dict[str, List[PHPMDOutput]]): The PHPMD output to
            append to the base.

    Returns:
        List[PDependWithPHPMD]: The combined output, where each PDependOutput
            now includes a list of associated PHPMD violations.
    """
    result: List[PDependWithPHPMD] = base.copy()

    for output_ in result:
        file_path = output_['file_path']
        start_line = output_['start_line']
        end_line = output_['end_line']

        output_['phpmd_violations'] = []

        if file_path in side_phpmd:
            for phpmd_output in side_phpmd[file_path]:
                if start_line <= phpmd_output['line'] <= end_line:
                    output_['phpmd_violations'].append(
                        PHPMDOutput(
                            line=phpmd_output['line'],
                            rule=phpmd_output['rule'],
                            message=phpmd_output['message'],
                        )
                    )

    return result


def main():
    _cwd = Path.cwd()

    ## Expected base location ##
    base_path = _cwd / 'outputs' / 'raw-output' / 'opencontext-engineblock'

    ## Style violations and class-based results are ignored for now ##
    parsed_output__base = parse_pdepend(str(base_path / 'pdepend.xml'))
    parsed_output__side_phpmd = parse_phpmd(str(base_path / 'phpmd.xml'))
    parsed_output = _append_side_phpmd_to_base(
        parsed_output__base, parsed_output__side_phpmd
    )

    ## Expected output location ##
    output_path = _cwd / 'outputs' / 'parsed-output' / 'opencontext-engineblock'
    output_path.mkdir(parents=True, exist_ok=True)

    ## Create CSV output ##
    with open(
        output_path / 'output.csv', 'w', newline='', encoding='utf-8'
    ) as file_:
        writer = csv_dict_writer(
            file_,
            fieldnames=[
                'file_path',
                'method_name',
                'start_line',
                'end_line',
                'cc',
                'mi',
                'halstead_difficulty',
                'amount_of_phpmd_violations',
                'phpmd_violations',
            ],
        )

        writer.writeheader()

        for row in parsed_output:
            writer.writerow(
                {
                    **row,
                    'amount_of_phpmd_violations': len(row['phpmd_violations']),
                    'phpmd_violations': str(row['phpmd_violations']),
                }
            )


if __name__ == '__main__':
    main()
