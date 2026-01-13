#!/usr/bin/env python3
"""
Mucher - Enhanced wrapper for the 'much' multiple-choice exam generator.

This module provides classes for generating randomized multiple-choice exams,
grading student responses, and generating analytics reports.

For more information about the underlying 'much' tool, see:
https://eigen-space.org/much/
"""

import argparse
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import jinja2
import matplotlib.pyplot as plt
import pandas as pd
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_NUM_TESTS = 30
DEFAULT_SERIAL_START = 10
DEFAULT_USAGE_PER_CATEGORY = 1
DEFAULT_SEED = 42

DEFAULT_POINTS_CORRECT = 4
DEFAULT_POINTS_MISSING = 1
DEFAULT_POINTS_INCORRECT = 0

QUESTIONS_PER_BLOCK = 5
RESPONSES_PER_QUESTION = 4

FIGURE_HEIGHT = 10
FIGURE_WIDTH = 15
BAR_WIDTH = 0.2

SUPPORTED_IMAGE_EXTENSIONS = ['jpg', 'gif', 'png', 'jpeg']

DEFAULT_QUESTION_FILE = 'questionario.xlsx'
DEFAULT_RESULTS_FILE = 'elaborati.xlsx'
DEFAULT_CONFIG_FILE = 'mucher_config.yaml'


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class ExamConfig:
    """Configuration for exam generation and grading.

    Attributes:
        question_file: Path to Excel file containing questions.
        num_tests: Number of test variants to generate.
        serial_start: Starting serial number for tests.
        usage_per_category: Number of questions to use from each category.
        seed: Random seed for reproducibility.
        points_correct: Points awarded for correct answers.
        points_missing: Points awarded for unanswered questions.
        points_incorrect: Points awarded for incorrect answers.
        results_file: Path to Excel file containing student responses.
        output_dir: Directory for output files.
        cleanup_temp: Whether to clean up temporary files after generation.
    """
    question_file: str = DEFAULT_QUESTION_FILE
    num_tests: int = DEFAULT_NUM_TESTS
    serial_start: int = DEFAULT_SERIAL_START
    usage_per_category: int = DEFAULT_USAGE_PER_CATEGORY
    seed: int = DEFAULT_SEED
    points_correct: int = DEFAULT_POINTS_CORRECT
    points_missing: int = DEFAULT_POINTS_MISSING
    points_incorrect: int = DEFAULT_POINTS_INCORRECT
    results_file: str = DEFAULT_RESULTS_FILE
    output_dir: str = '.'
    cleanup_temp: bool = True

    @classmethod
    def from_yaml(cls, filepath: str) -> 'ExamConfig':
        """Load configuration from a YAML file.

        Args:
            filepath: Path to the YAML configuration file.

        Returns:
            ExamConfig instance with values from the file.

        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
            yaml.YAMLError: If the file contains invalid YAML.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        logger.info(f"Loading configuration from {filepath}")
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_yaml(self, filepath: str) -> None:
        """Save configuration to a YAML file.

        Args:
            filepath: Path where the configuration file will be saved.
        """
        path = Path(filepath)
        data = {
            'question_file': self.question_file,
            'num_tests': self.num_tests,
            'serial_start': self.serial_start,
            'usage_per_category': self.usage_per_category,
            'seed': self.seed,
            'points_correct': self.points_correct,
            'points_missing': self.points_missing,
            'points_incorrect': self.points_incorrect,
            'results_file': self.results_file,
            'output_dir': self.output_dir,
            'cleanup_temp': self.cleanup_temp,
        }

        logger.info(f"Saving configuration to {filepath}")
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


# =============================================================================
# LaTeX Template
# =============================================================================

def get_latex_template() -> str:
    """Return the LaTeX template for exam documents.

    Returns:
        String containing the LaTeX template with placeholders for
        exam content generated by 'much'.
    """
    return r"""
\documentclass[11pt,a4paper]{article}
\usepackage{amsfonts,latexsym}
\usepackage[italian]{babel}
\usepackage{amsfonts}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{fullpage}
\usepackage{graphicx}
\usepackage{wrapfig}
\usepackage{siunitx}
\usepackage{physics}
\usepackage{multicol}
\usepackage{geometry}
\usepackage{microtype}

\geometry{top=0.7cm, bottom=0.7cm, left=1cm, right=1cm}

\begin{document}

\pagestyle{empty}

\newcommand{\mcglobalheader}{
}

\newcommand{\boxt}{{\Huge $\square$ }}

\newcommand{\mcpaperheader}{
\ \\
TESTO NUMERO \mcserialnumber. STUDENTE: \\
{\textbf{Tempo a disposizione: XXXX.} In ognuna delle seguenti domande una sola opzione è corretta.
\\ Risposta corretta: XX punti. Risposta non data: XX punti. Risposta errata: XX punti.}

\begin{center}
{\Large Verifica di XXX n.XX: XXXX}\\
Classe XX, XX/XX/20XX.
\end{center}
}



\newcommand{\mcpaperfooter}{



\newpage
}

\newcommand{\mcquestionheader}{\noindent{\bf \mcquestionnumber}. }

\newcommand{\mcquestionfooter}{}

\input mc-output.tex

\end{document}
"""


# =============================================================================
# Exam Generator
# =============================================================================

class ExamGenerator:
    """Generates randomized multiple-choice exams using the 'much' tool.

    This class handles the entire exam generation pipeline:
    1. Parsing questions from Excel files
    2. Creating configuration files for 'much'
    3. Running 'much' to generate randomized exams
    4. Compiling the LaTeX output to PDF

    Attributes:
        config: ExamConfig instance with generation settings.
    """

    def __init__(self, config: ExamConfig):
        """Initialize the exam generator.

        Args:
            config: Configuration settings for exam generation.
        """
        self.config = config
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None
        self._temp_path: Optional[Path] = None

    def _validate_input_file(self, filepath: str) -> Path:
        """Validate that an input file exists and is readable.

        Args:
            filepath: Path to the file to validate.

        Returns:
            Path object for the validated file.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            PermissionError: If the file isn't readable.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {filepath}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {filepath}")
        if not os.access(path, os.R_OK):
            raise PermissionError(f"Cannot read file: {filepath}")

        logger.debug(f"Validated input file: {filepath}")
        return path

    def _setup_temp_directory(self) -> Path:
        """Create a temporary directory for intermediate files.

        Returns:
            Path to the temporary directory.
        """
        self._temp_dir = tempfile.TemporaryDirectory(prefix='mucher_')
        self._temp_path = Path(self._temp_dir.name)
        logger.debug(f"Created temporary directory: {self._temp_path}")
        return self._temp_path

    def _cleanup_temp_directory(self) -> None:
        """Clean up the temporary directory if configured to do so."""
        if self._temp_dir is not None and self.config.cleanup_temp:
            try:
                self._temp_dir.cleanup()
                logger.debug("Cleaned up temporary directory")
            except OSError as e:
                logger.warning(f"Failed to clean up temporary directory: {e}")
            finally:
                self._temp_dir = None
                self._temp_path = None

    def _generate_latex_template(self, folder: Path) -> None:
        """Write the LaTeX template to a file.

        Args:
            folder: Directory where the template will be written.
        """
        template_path = folder / "exam.tex"
        template_path.write_text(get_latex_template(), encoding='utf-8')
        logger.debug(f"Generated LaTeX template: {template_path}")

    def _parse_questions_from_excel(self, folder: Path) -> list[str]:
        """Parse questions from an Excel file and create question files.

        Each sheet in the Excel file represents a category of questions.
        Questions are written to individual files for 'much' to process.

        Args:
            folder: Directory where question files will be written.

        Returns:
            List of sheet names (question categories) found in the file.

        Raises:
            ValueError: If the Excel file has an invalid structure.
        """
        input_path = self._validate_input_file(self.config.question_file)

        logger.info(f"Parsing questions from {input_path}")
        excel_file = pd.ExcelFile(input_path)
        sheets = excel_file.sheet_names

        if not sheets:
            raise ValueError(f"Excel file has no sheets: {input_path}")

        for sheet in sheets:
            elements = excel_file.parse(sheet, header=None).values

            if len(elements) == 0:
                logger.warning(f"Sheet '{sheet}' is empty, skipping")
                continue

            if len(elements) == QUESTIONS_PER_BLOCK:
                # Single question in sheet
                self._write_question_file(folder, sheet, 0, elements, 0)
            elif len(elements) % QUESTIONS_PER_BLOCK == 0:
                # Multiple questions in sheet
                num_questions = len(elements) // QUESTIONS_PER_BLOCK
                for i in range(num_questions):
                    start_idx = i * QUESTIONS_PER_BLOCK
                    self._write_question_file(folder, sheet, i, elements, start_idx)
            else:
                logger.warning(
                    f"Sheet '{sheet}' has {len(elements)} rows, expected multiple of "
                    f"{QUESTIONS_PER_BLOCK}. Some questions may be skipped."
                )
                num_questions = len(elements) // QUESTIONS_PER_BLOCK
                for i in range(num_questions):
                    start_idx = i * QUESTIONS_PER_BLOCK
                    self._write_question_file(folder, sheet, i, elements, start_idx)

        logger.info(f"Parsed {len(sheets)} question categories")
        return sheets

    def _write_question_file(
        self,
        folder: Path,
        sheet: str,
        index: int,
        elements: Any,
        start_idx: int
    ) -> None:
        """Write a single question to a file in 'much' format.

        Args:
            folder: Directory for the question file.
            sheet: Sheet name (used as category prefix).
            index: Question index within the sheet.
            elements: Array of question data from Excel.
            start_idx: Starting index in elements array.
        """
        filename = folder / f"{sheet}-{index}"

        # Validate array bounds
        if start_idx >= len(elements):
            logger.warning(f"Invalid start index {start_idx} for sheet '{sheet}'")
            return

        question_row = elements[start_idx]
        if len(question_row) == 0 or pd.isna(question_row[0]):
            logger.warning(f"Empty question in sheet '{sheet}' at index {index}")
            return

        question = str(question_row[0]).strip()

        # Extract responses with bounds checking
        responses = []
        for i in range(1, RESPONSES_PER_QUESTION + 1):
            resp_idx = start_idx + i
            if resp_idx < len(elements) and len(elements[resp_idx]) > 0:
                resp_value = elements[resp_idx][0]
                if not pd.isna(resp_value):
                    responses.append(str(resp_value).strip())

        if len(responses) < RESPONSES_PER_QUESTION:
            logger.warning(
                f"Question in sheet '{sheet}' at index {index} has only "
                f"{len(responses)} responses (expected {RESPONSES_PER_QUESTION})"
            )

        content = question + "\n.\n" + "\n.\n".join(responses) + "\n.\n"
        filename.write_text(content, encoding='utf-8')
        logger.debug(f"Wrote question file: {filename}")

    def _generate_much_description(self, sheets: list[str], folder: Path) -> None:
        """Generate the description file for 'much'.

        Args:
            sheets: List of question category names.
            folder: Directory where the description file will be written.
        """
        usages = [
            f'use {self.config.usage_per_category} from "{sheet}-*";'
            for sheet in sheets
        ]

        description = f'''
directory ".";
seed {self.config.seed};
serial {self.config.serial_start};
{chr(10).join(usages)}
create {self.config.num_tests};'''

        desc_path = folder / "description"
        desc_path.write_text(description, encoding='utf-8')
        logger.debug(f"Generated much description file: {desc_path}")

    def _run_much(self, folder: Path) -> None:
        """Execute the 'much' tool to generate exam variants.

        Args:
            folder: Working directory containing input files.

        Raises:
            subprocess.CalledProcessError: If 'much' fails.
            FileNotFoundError: If 'much' is not installed.
        """
        logger.info("Running 'much' to generate exam variants")

        try:
            result = subprocess.run(
                ['much'],
                input='c\ndescription\n',
                cwd=folder,
                capture_output=True,
                text=True,
                check=True
            )
            logger.debug(f"much stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"much stderr: {result.stderr}")
        except FileNotFoundError:
            raise FileNotFoundError(
                "The 'much' tool is not installed or not in PATH. "
                "Please install it from https://eigen-space.org/much/"
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"much failed: {e.stderr}")
            raise

    def _copy_images(self, folder: Path) -> None:
        """Copy image files to the working directory.

        Args:
            folder: Destination directory for images.
        """
        for ext in SUPPORTED_IMAGE_EXTENSIONS:
            for img_file in Path('.').glob(f'*.{ext}'):
                try:
                    dest = folder / img_file.name
                    shutil.copy2(img_file, dest)
                    logger.debug(f"Copied image: {img_file} -> {dest}")
                except (OSError, shutil.Error) as e:
                    logger.warning(f"Failed to copy image {img_file}: {e}")

    def _compile_latex(self, folder: Path) -> None:
        """Compile the LaTeX file to PDF.

        Args:
            folder: Directory containing the LaTeX file.

        Raises:
            subprocess.CalledProcessError: If pdflatex fails.
            FileNotFoundError: If pdflatex is not installed.
        """
        logger.info("Compiling LaTeX to PDF")

        try:
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', 'exam.tex'],
                cwd=folder,
                capture_output=True,
                text=True,
                check=False  # pdflatex may return non-zero even on success
            )

            # Check if PDF was created
            pdf_path = folder / 'exam.pdf'
            if not pdf_path.exists():
                logger.error(f"pdflatex output: {result.stdout}")
                raise RuntimeError("pdflatex failed to create PDF")

            logger.debug("LaTeX compilation successful")
        except FileNotFoundError:
            raise FileNotFoundError(
                "pdflatex is not installed. Please install a LaTeX distribution."
            )

    def _copy_output_files(self, folder: Path) -> None:
        """Copy generated files to the output directory.

        Args:
            folder: Source directory containing generated files.
        """
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy PDF
        pdf_src = folder / 'exam.pdf'
        if pdf_src.exists():
            shutil.copy2(pdf_src, output_dir / 'exam.pdf')
            logger.info(f"Created: {output_dir / 'exam.pdf'}")

        # Copy LaTeX source
        tex_src = folder / 'exam.tex'
        if tex_src.exists():
            shutil.copy2(tex_src, output_dir / 'exam.tex')
            logger.info(f"Created: {output_dir / 'exam.tex'}")

        # Create grading spreadsheet from serial numbers
        serials_path = folder / 'mc-serials.txt'
        if serials_path.exists():
            try:
                df = pd.read_csv(serials_path, sep=' ', skiprows=1, header=None)
                output_xlsx = output_dir / self.config.results_file
                df.to_excel(output_xlsx, index=False)
                logger.info(f"Created: {output_xlsx}")
            except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
                logger.error(f"Failed to parse serial numbers file: {e}")

    def generate(self) -> None:
        """Execute the full exam generation pipeline.

        This method:
        1. Sets up a temporary working directory
        2. Parses questions from the Excel file
        3. Generates 'much' configuration
        4. Runs 'much' to create exam variants
        5. Compiles the LaTeX output
        6. Copies results to the output directory

        Raises:
            FileNotFoundError: If required input files or tools are missing.
            ValueError: If input data is invalid.
            subprocess.CalledProcessError: If external tools fail.
        """
        logger.info("Starting exam generation")

        try:
            folder = self._setup_temp_directory()

            self._generate_latex_template(folder)
            sheets = self._parse_questions_from_excel(folder)
            self._generate_much_description(sheets, folder)
            self._copy_images(folder)
            self._run_much(folder)
            self._compile_latex(folder)
            self._copy_output_files(folder)

            logger.info("Exam generation completed successfully")

        finally:
            self._cleanup_temp_directory()


# =============================================================================
# Exam Grader
# =============================================================================

@dataclass
class GradingResult:
    """Results from grading student responses.

    Attributes:
        scores: DataFrame with student scores.
        report: Dictionary with statistics by question category.
    """
    scores: pd.DataFrame
    report: dict[str, dict[str, int]]


class ExamGrader:
    """Grades student responses and generates statistics.

    This class processes Excel files containing student responses,
    calculates scores based on configured point values, and generates
    per-question statistics.

    Attributes:
        config: ExamConfig instance with grading settings.
    """

    # Column indices in the results file
    MIN_COLUMNS_REQUIRED = 6
    MODEL_COL_IDX = 2
    QUESTIONS_START_IDX = 3
    QUESTIONS_END_OFFSET = -3
    CORRECT_ANSWERS_OFFSET = -3
    GIVEN_ANSWERS_OFFSET = -2
    STUDENT_ID_OFFSET = -1

    def __init__(self, config: ExamConfig):
        """Initialize the exam grader.

        Args:
            config: Configuration settings for grading.
        """
        self.config = config

    def _validate_results_file(self) -> Path:
        """Validate that the results file exists and is readable.

        Returns:
            Path to the validated results file.

        Raises:
            FileNotFoundError: If the file doesn't exist.
        """
        path = Path(self.config.results_file)
        if not path.exists():
            raise FileNotFoundError(
                f"Results file not found: {self.config.results_file}"
            )
        logger.info(f"Loading results from {path}")
        return path

    def _validate_row(self, row: list, row_idx: int) -> bool:
        """Validate that a row has the expected structure.

        Args:
            row: List of values from the row.
            row_idx: Row index for error messages.

        Returns:
            True if the row is valid, False otherwise.
        """
        if len(row) < self.MIN_COLUMNS_REQUIRED:
            logger.warning(
                f"Row {row_idx} has only {len(row)} columns, "
                f"expected at least {self.MIN_COLUMNS_REQUIRED}"
            )
            return False
        return True

    def grade(self) -> GradingResult:
        """Grade all student responses and generate statistics.

        Returns:
            GradingResult containing scores and per-question statistics.

        Raises:
            FileNotFoundError: If the results file doesn't exist.
            ValueError: If the file format is invalid.
        """
        results_path = self._validate_results_file()
        df = pd.read_excel(results_path)

        if df.empty:
            raise ValueError(f"Results file is empty: {results_path}")

        # Initialize report structure
        report: dict[str, dict[str, int]] = {}
        scores: list[Any] = []

        # Process each row using vectorized operations where possible
        for row_idx, row_data in df.iterrows():
            row = list(row_data)

            if not self._validate_row(row, row_idx):
                scores.append('')
                continue

            # Extract data with bounds checking
            given_answers = row[self.GIVEN_ANSWERS_OFFSET]

            # Skip rows without valid answers
            if not isinstance(given_answers, str):
                scores.append('')
                continue

            correct_answers = row[self.CORRECT_ANSWERS_OFFSET]
            questions = row[self.QUESTIONS_START_IDX:self.QUESTIONS_END_OFFSET]

            # Calculate score for this student
            student_score = self._calculate_student_score(
                correct_answers,
                given_answers,
                questions,
                report
            )
            scores.append(student_score)

        # Add scores to DataFrame
        df['PUNTEGGI'] = scores

        # Save graded results
        output_path = results_path.stem + '_corretti.xlsx'
        df.to_excel(output_path, index=False)
        logger.info(f"Saved graded results to {output_path}")

        return GradingResult(scores=df, report=report)

    def _calculate_student_score(
        self,
        correct_answers: str,
        given_answers: str,
        questions: list,
        report: dict[str, dict[str, int]]
    ) -> int:
        """Calculate the score for a single student.

        Args:
            correct_answers: String of correct answer letters.
            given_answers: String of answers given by student.
            questions: List of question identifiers.
            report: Dictionary to update with statistics.

        Returns:
            Total score for the student.
        """
        total_score = 0

        for correct, given, question in zip(correct_answers, given_answers, questions):
            # Extract question category (remove trailing index)
            question_str = str(question)
            if len(question_str) >= 2:
                category = question_str[:-2]
            else:
                category = question_str

            # Initialize category in report if needed
            if category not in report:
                report[category] = {'corrette': 0, 'non date': 0, 'errate': 0}

            # Score the answer
            if given == '-':
                total_score += self.config.points_missing
                report[category]['non date'] += 1
            elif correct == given:
                total_score += self.config.points_correct
                report[category]['corrette'] += 1
            else:
                total_score += self.config.points_incorrect
                report[category]['errate'] += 1

        return total_score


# =============================================================================
# Report Generator
# =============================================================================

class ReportGenerator:
    """Generates visual reports from grading results.

    This class creates charts and visualizations showing answer
    distributions across question categories.
    """

    def __init__(self, output_filename: str = 'valutazioni'):
        """Initialize the report generator.

        Args:
            output_filename: Base name for output files (without extension).
        """
        self.output_filename = output_filename

    def generate_response_chart(self, report: dict[str, dict[str, int]]) -> None:
        """Generate a stacked bar chart showing response distribution.

        Args:
            report: Dictionary with statistics by question category,
                   as returned by ExamGrader.grade().
        """
        if not report:
            logger.warning("No data to generate chart")
            return

        # Extract data using list comprehensions (more efficient than loops)
        categories = list(report.keys())
        correct = [report[q]['corrette'] for q in categories]
        missing = [report[q]['non date'] for q in categories]
        incorrect = [report[q]['errate'] for q in categories]

        # Calculate stacked positions
        correct_plus_missing = [c + m for c, m in zip(correct, missing)]

        # Create figure
        fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

        # Create stacked bars
        ax.bar(categories, correct, BAR_WIDTH, label='corrette', color='tab:blue')
        ax.bar(categories, missing, BAR_WIDTH, bottom=correct,
               label='non date', color='tab:gray')
        ax.bar(categories, incorrect, BAR_WIDTH, bottom=correct_plus_missing,
               label='errate', color='tab:olive')

        ax.set_ylabel('Valore assoluto')
        ax.set_xlabel('Domande')
        ax.set_title('Report by question')
        ax.legend()

        # Rotate labels if many categories
        if len(categories) > 10:
            plt.xticks(rotation=45, ha='right')

        output_path = f'{self.output_filename}_analisi_risposte.png'
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close(fig)

        logger.info(f"Generated response chart: {output_path}")


# =============================================================================
# CLI Interface
# =============================================================================

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the command-line argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description='Mucher - Enhanced wrapper for the much exam generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  Generate exams:     python mucher.py -a c -f questions.xlsx -n 30
  Grade responses:    python mucher.py -a v -v responses.xlsx
  Use config file:    python mucher.py -a c --config config.yaml
  Generate template:  python mucher.py --generate-config
        '''
    )

    parser.add_argument(
        '-a', '--azione',
        help='Action: [c]reate or [v]alidate/grade exams',
        choices=['c', 'v'],
        default='c'
    )
    parser.add_argument(
        '-f', '--filename',
        help=f'Excel file with questions (default: {DEFAULT_QUESTION_FILE})',
        default=DEFAULT_QUESTION_FILE
    )
    parser.add_argument(
        '-n', '--numero',
        help=f'Number of test variants to generate (default: {DEFAULT_NUM_TESTS})',
        type=int,
        default=DEFAULT_NUM_TESTS
    )
    parser.add_argument(
        '-c', '--corrette',
        help=f'Points for correct answer (default: {DEFAULT_POINTS_CORRECT})',
        type=int,
        default=DEFAULT_POINTS_CORRECT
    )
    parser.add_argument(
        '-m', '--missing',
        help=f'Points for unanswered question (default: {DEFAULT_POINTS_MISSING})',
        type=int,
        default=DEFAULT_POINTS_MISSING
    )
    parser.add_argument(
        '-i', '--incorrette',
        help=f'Points for incorrect answer (default: {DEFAULT_POINTS_INCORRECT})',
        type=int,
        default=DEFAULT_POINTS_INCORRECT
    )
    parser.add_argument(
        '-v', '--valutazione',
        help=f'Excel file with student responses (default: {DEFAULT_RESULTS_FILE})',
        default=DEFAULT_RESULTS_FILE
    )
    parser.add_argument(
        '-s', '--seed',
        help=f'Random seed for reproducibility (default: {DEFAULT_SEED})',
        type=int,
        default=DEFAULT_SEED
    )
    parser.add_argument(
        '--config',
        help='Path to YAML configuration file',
        default=None
    )
    parser.add_argument(
        '--generate-config',
        help='Generate a template configuration file and exit',
        action='store_true'
    )
    parser.add_argument(
        '--no-cleanup',
        help='Do not delete temporary files after generation',
        action='store_true'
    )
    parser.add_argument(
        '--verbose',
        help='Enable verbose logging',
        action='store_true'
    )

    return parser


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_argument_parser()
    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Generate config template if requested
    if args.generate_config:
        config = ExamConfig()
        config.to_yaml(DEFAULT_CONFIG_FILE)
        print(f"Generated configuration template: {DEFAULT_CONFIG_FILE}")
        return 0

    # Load configuration
    try:
        if args.config:
            config = ExamConfig.from_yaml(args.config)
            # Override with CLI arguments if provided
            if args.filename != DEFAULT_QUESTION_FILE:
                config.question_file = args.filename
            if args.numero != DEFAULT_NUM_TESTS:
                config.num_tests = args.numero
            if args.corrette != DEFAULT_POINTS_CORRECT:
                config.points_correct = args.corrette
            if args.missing != DEFAULT_POINTS_MISSING:
                config.points_missing = args.missing
            if args.incorrette != DEFAULT_POINTS_INCORRECT:
                config.points_incorrect = args.incorrette
            if args.valutazione != DEFAULT_RESULTS_FILE:
                config.results_file = args.valutazione
            if args.seed != DEFAULT_SEED:
                config.seed = args.seed
        else:
            config = ExamConfig(
                question_file=args.filename,
                num_tests=args.numero,
                seed=args.seed,
                points_correct=args.corrette,
                points_missing=args.missing,
                points_incorrect=args.incorrette,
                results_file=args.valutazione,
                cleanup_temp=not args.no_cleanup
            )
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML configuration: {e}")
        return 1

    # Execute requested action
    try:
        if args.azione == 'c':
            generator = ExamGenerator(config)
            generator.generate()

        elif args.azione == 'v':
            grader = ExamGrader(config)
            result = grader.grade()

            reporter = ReportGenerator()
            reporter.generate_response_chart(result.report)

        return 0

    except FileNotFoundError as e:
        logger.error(str(e))
        return 1
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return 1
    except subprocess.CalledProcessError as e:
        logger.error(f"External command failed: {e}")
        return 1
    except PermissionError as e:
        logger.error(f"Permission denied: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
