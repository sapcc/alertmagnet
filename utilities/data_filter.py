def remove_state_from_timestamp_value(
    data: list[list],
) -> list[int]:  # expected list structure e.g. result matrix from prometheus
    """Expected input structure:
    [[timestamp, state], …]
    >>> produced output:
    [timestamp, …]
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


def create_time_ranges(
    data: list[float], step: int
) -> list[tuple]:  # expected list structure e.g. result matrix from prometheus
    """Expected input structure data:
    [timestamp, …]
    >>> produced output:
    [(timestamp, duration), …]
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

        if not value == prev + step:  # consider using >
            out.append((start, prev - start))
            start = prev = value
            continue

        prev = value

    value = data[-1]
    if start is None:
        out.append((value, 0))
    else:
        if not value == prev + step:  # consider using >
            out.append((start, prev - start))
            out.append((value, 0))
        else:
            out.append((start, value - start))

    return out
