import csv
import io
from typing import Generator


def generate_csv_stream(records_generator) -> Generator[str, None, None]:
    """Yields CSV rows one at a time for memory-efficient streaming."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["ID", "User ID", "Amount", "Type", "Category", "Date", "Notes", "Created At"])
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    for record in records_generator:
        writer.writerow([
            record.id, record.user_id, str(record.amount),
            record.type.value if record.type else "", record.category,
            str(record.date), record.notes or "", str(record.created_at),
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
