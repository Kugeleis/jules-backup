import re


def apply_git_merge_diff(
    original_content: str, diff_text: str
) -> tuple[bool, str, str]:
    """
    Applies search and replace blocks formatted with Git merge conflict markers:
    <<<<<<< SEARCH
    old code
    =======
    new code
    >>>>>>> REPLACE

    Returns:
        (success: bool, updated_content: str, error_message: str)
    """
    pattern: re.Pattern[str] = re.compile(
        r"<<<<<<< SEARCH\r?\n(.*?)\r?\n=======\r?\n(.*?)\r?\n>>>>>>> REPLACE", re.DOTALL
    )
    matches: list[re.Match[str]] = list(pattern.finditer(diff_text))

    if not matches:
        return (
            False,
            original_content,
            "No valid Git merge diff blocks found. Format: <<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE",
        )

    content = original_content
    for match in matches:
        search_block = match.group(1)
        replace_block = match.group(2)

        # Check if search block is in content
        if search_block not in content:
            # Try normalizing newlines
            norm_content = content.replace("\r\n", "\n")
            norm_search = search_block.replace("\r\n", "\n")
            norm_replace = replace_block.replace("\r\n", "\n")

            if norm_search not in norm_content:
                return (
                    False,
                    original_content,
                    f"Search block not found in target file:\n{search_block[:120]}...",
                )
            content = norm_content.replace(norm_search, norm_replace, 1)
        else:
            content = content.replace(search_block, replace_block, 1)

    return True, content, ""
