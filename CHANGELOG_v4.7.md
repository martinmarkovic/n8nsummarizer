# v4.7 Changelog - Recursive Subfolder Scanning

**Release Date:** January 6, 2026
**Base:** v4.6 (clean N8N/LM Studio output)

## Features Added

### Recursive Subfolder Scanning

✨ **NEW** - Bulk summarizer now supports recursive subfolder scanning with the following features:

#### User Interface Changes

1. **New Checkbox Option** (`views/bulk_summarizer_tab.py`)
   - Added "Scan Subfolders (recursive scanning)" checkbox in the "Scanning Options" section
   - Located between file type selection and output format options
   - Includes helpful info text: "When enabled: Scans all subfolders and maintains folder structure in output"
   - Option is saved to `.env` file as `BULK_RECURSIVE_SUBFOLDERS`
   - Preference persists between sessions

#### Controller Logic (`controllers/bulk_summarizer_controller.py`)

1. **File Discovery**
   - `_discover_files()` now accepts `recursive` parameter
   - When `recursive=True`: Uses `Path.rglob()` to scan all nested subfolders
   - When `recursive=False`: Uses `Path.glob()` for current folder only (default behavior)
   - Works with all file types (txt, srt, docx, pdf)

2. **Folder Structure Preservation**
   - Output folder automatically mirrors the source folder structure
   - Each subfolder in source gets a corresponding subfolder in output
   - Example:
     ```
     Source:
       /Documents/
         file1.txt
         /subfolder1/
           file2.txt
         /subfolder2/
           file3.txt
     
     Output (with recursive enabled):
       /Documents - Summarized/
         file1_summary.txt
         /subfolder1/
           file2_summary.txt
         /subfolder2/
           file3_summary.txt
     ```

3. **Combined Summary with Paths**
   - When combined output is selected with recursive scanning:
   - File paths in combined summary show the relative path
   - Example entry in combined file: `===== subfolder1/file2.txt =====`
   - Helps identify which files came from which subfolder

#### Background Processing

1. **Threading & Progress**
   - All files processed sequentially, preserving folder structure in real-time
   - Progress bar and file counter work correctly with all discovered files
   - Status log shows file processing regardless of folder depth

2. **Error Handling**
   - If a file fails, logging includes the file's relative path
   - Failed file list maintained for completion summary
   - Processing continues in other folders if one fails

#### File Counting

- File count in UI (`_count_matching_files()`) updates correctly when recursive option toggled
- Shows total files found across all folders
- Updates immediately in the status log

## Implementation Details

### Code Changes

**views/bulk_summarizer_tab.py**
- Added `self.recursive_subfolders` BooleanVar
- New method `_setup_recursive_option()` creates UI section
- New method `_on_recursive_changed()` handles option toggle
- Updated `_count_matching_files()` to use `rglob()` when recursive enabled
- Updated preferences loading/saving to include `BULK_RECURSIVE_SUBFOLDERS`
- Added `get_recursive_option()` public method
- Updated row numbering for new UI section

**controllers/bulk_summarizer_controller.py**
- Updated `handle_start_processing()` to get recursive option from view
- Updated `_discover_files()` to accept and handle `recursive` parameter
- Updated `_process_folder_background()` to accept `recursive` parameter
- Added subfolder structure creation logic in processing loop
- Updated relative path calculation for combined summaries
- Enhanced logging for recursive operations

## Usage Example

### Default Behavior (recursive OFF)

1. Select a folder: `/path/to/Documents`
2. Only files directly in `/path/to/Documents` are scanned
3. Output: `Documents - Summarized/` (flat structure)

### With Recursive Enabled (NEW)

1. Select a folder: `/path/to/Documents`
2. Entire directory tree is scanned (all subdirectories)
3. Output maintains same structure: `Documents - Summarized/` with all subfolders
4. Combined summary includes relative paths

## Backward Compatibility

✅ **Fully backward compatible**
- Default behavior unchanged (recursive = OFF)
- Existing workflows unaffected
- Option only activates when checkbox is enabled
- Preferences stored in `.env` file (new variable only)

## Testing Recommendations

1. **Test without recursion** (default behavior)
   - Verify single-folder processing works as before
   - Check output naming and structure

2. **Test with recursion enabled**
   - Test with folder containing 2-3 levels of subfolders
   - Verify folder structure is preserved in output
   - Check combined summary includes paths

3. **Test edge cases**
   - Empty subfolders (should be skipped)
   - Subfolders with no matching files
   - Toggle recursive on/off and verify file count updates
   - Mixed file types in different subfolders

4. **Test with combined output**
   - Verify combined summary shows relative paths
   - Check that files are grouped logically

## Version History

| Version | Date | Changes |
|---------|------|----------|
| v4.7 | 2026-01-06 | **Recursive subfolder scanning** |
| v4.6 | 2026-01-05 | Remove multi-chunk wrapper text |
| v4.5 | Earlier | Previous versions |

## Future Enhancements

💡 Possible future improvements:
- Option to exclude certain folders from recursive scan
- Depth limit for recursion
- Filter by folder name pattern
- Option to create one combined file per subfolder
