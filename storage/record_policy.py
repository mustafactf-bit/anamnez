"""Production records retain the physician-approved text, never raw dictation."""
from copy import deepcopy


def prepare_record(values: dict, snapshot: dict, *, test_mode: bool = False,
                   raw_transcript: str = '') -> dict:
    """Strip the application's known deprecated raw fields without editing originals."""
    record=deepcopy(values)
    record.pop('_note_draft',None)
    record.pop('_test_data',None)
    if not test_mode:
        if not snapshot.get('last_approved_text'):
            raise ValueError('Kaydetmeden önce son metni onaylayın.')
        record['_note_draft']={key:snapshot[key] for key in
            ('body','last_approved_text','approved_at','sources_current') if key in snapshot}
    else:
        record['_note_draft']=deepcopy(snapshot)
        record['_test_data']={'raw_transcript':raw_transcript,'test_only':True}
    return record


def without_legacy_raw(loaded: dict) -> tuple[dict,dict | None]:
    """Import old records without retaining their raw extension in production memory."""
    values=deepcopy(loaded)
    note=values.pop('_note_draft',None)
    values.pop('_test_data',None)
    if isinstance(note,dict):
        note={key:note[key] for key in ('body','last_approved_text','approved_at','sources_current') if key in note}
    return values,note
