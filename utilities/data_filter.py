def remove_state_from_timestamp_value(data: list[list]) -> list[int]:
    """
    Extracts the first element (assumed to be a timestamp) from each sublist in the input list.

    Args:
        data (list[list]): A list of lists, where each sublist contains at least one element,
                           and the first element is expected to be a float representing a timestamp.

    Returns:
        list[int]: A list of the first elements (timestamps) from each sublist in the input list.

    Raises:
        TypeError: If the input data is not a list of lists, or if the first element of any sublist is not a float.
    """

    out = []

    if not isinstance(data, list):
        raise TypeError(f"Invalid input format: isinstance(data, list) = {isinstance(data, list)}; type: {type(data)}")

    for value in data:
        if not isinstance(value, list):
            raise TypeError(
                f"Invalid input format: isinstance(value, list) = {isinstance(value, list)}; type: {type(value)}"
            )

        if not isinstance(value[0], float):
            raise TypeError(
                f"Invalid input format: isinstance(value[0], float) = {isinstance(value[0], float)}; type: {type(value[0])}"
            )

        out.append(value[0])

    return out


def create_time_ranges(data: list[float], step: int) -> list[tuple]:
    """
    Create time ranges from a list of float values.

    This function takes a list of float values and a step value, and returns a list of tuples.
    Each tuple represents a time range, where the first element is the start value and the second
    element is the duration (difference between the start and end values).

    Args:
        data (list[float]): A list of float values representing time points.
        step (int): The step value to determine the continuity of the time ranges.

    Returns:
        list[tuple]: A list of tuples, where each tuple contains the start value and the duration
                     of a time range.

    Raises:
        TypeError: If the input data is not a list.

    Example:
        >>> create_time_ranges([1.0, 2.0, 3.0, 5.0, 6.0], 1)
        [(1.0, 2.0), (5.0, 1.0)]
    """

    if not isinstance(data, list):
        raise TypeError(f"Invalid input format: isinstance(data, list) = {isinstance(data, list)}; type: {type(data)}")

    out = []

    start = None
    prev = None

    if len(data) == 0:
        return out

    for value in data[:-1]:
        if start is None:
            start = prev = value
            continue

        if value == prev:
            continue

        if value != prev + step:  # consider using >
            out.append((start, prev - start))
            start = prev = value
            continue

        prev = value

    value = data[-1]
    if start is None:
        out.append((value, 0))
        return out

    if not value == prev + step:  # consider using >
        out.append((start, prev - start))
        out.append((value, 0))
    else:
        out.append((start, value - start))

    return out
