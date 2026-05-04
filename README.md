# Data Piece

Data Piece is a console-based application designed to streamline the process of data collection from the popular manga series, [One Piece](https://en.wikipedia.org/wiki/One_Piece). It provides an interactive interface for extracting detailed information from each chapter, page, and panel of the manga for data analysis purposes.

## Features

- Connects to a SQLite database.
- Handles database queries and executes SQL commands.
- Provides command completion options.
- Gracefully handles RuntimeErrors.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/alepiaz/datapiece.git
    ```
2. Navigate to the project directory:
    ```bash
    cd datapiece
    ```
3. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

To start the console, run the following command:
```bash
python main.py --config config/config.json
```

## Database structure
![ERM](img/erd.png?raw=True)


## CLI Reference

Start the console:
```bash
python main.py --config config/config.json
```

The prompt shows your current position in the manga hierarchy:
```
[V1/C5] >>>
```

### Session commands

| Command | Description |
|---|---|
| `status` | Show current volume / arc / chapter / page / panel |
| `start_volume <number> [date]` | Open a volume as your active context. Creates it in the database if it does not exist yet. Resets chapter context. Date format: `YYYY-MM-DD`. |
| `start_chapter <number> [arc_id] [name] [pub_date] [page_count]` | Add a chapter inside the active volume and move into it. If `arc_id` is omitted the last used arc is reused automatically. Trailing tokens are detected by type: a `YYYY-MM-DD` date becomes `pub_date`, a trailing integer becomes `page_count`, everything in between becomes the name. |

### Metadata setup (run once)

| Command | Description |
|---|---|
| `add_saga <name> <order>` | Create a saga. The last token is the order number; everything before it is the name. Prints the generated ID. |
| `add_arc <saga_id> <name> <order>` | Create an arc inside a saga. First token is `saga_id`, last is `order`, middle is the name. Prints the generated ID. |

### List / lookup commands

| Command | Description |
|---|---|
| `list_sagas` | All sagas ordered by position. |
| `list_arcs [saga_id]` | All arcs, optionally filtered to one saga. |
| `list_volumes` | All volumes ordered by number. |
| `list_chapters <arc_id>` | All chapters in an arc ordered by number. |

### Typical first session

```
# One-time saga / arc setup
>>> add_saga East Blue 1
Saga 'East Blue' added  [ID 1].
>>> add_arc 1 Romance Dawn 1
Arc 'Romance Dawn' added  [ID 1].
>>> add_arc 1 Orange Town 2
Arc 'Orange Town' added  [ID 2].
>>> add_arc 1 Syrup Village 3
>>> add_arc 1 Baratie 4
>>> add_arc 1 Arlong Park 5

# Start entering volumes and chapters
>>> start_volume 1 1997-12-24
Now in Volume 1.
[V1] >>> start_chapter 1 1 Romance Dawn 1997-07-22 53
Chapter 1 'Romance Dawn' added. Now in Chapter 1.
[V1/C1] >>> start_chapter 2 They Call Him Straw Hat Luffy 1997-07-29 21
Chapter 2 added. Now in Chapter 2.
[V1/C2] >>> start_chapter 3 ...

# arc_id is remembered — no need to repeat it for the same arc
# Switch arcs by providing the new arc_id in the next start_chapter call
[V1/C7] >>> start_chapter 8 2 Nami 1997-09-09 19
```

### Safeguards

- `start_volume` and `start_chapter` warn you if you switch context mid-session (e.g. you were on chapter 5 but jump to a different volume).
- `add_arc` refuses to insert if the parent saga does not exist.
- `start_chapter` refuses to insert if the arc does not exist.
- `start_chapter` refuses if no volume is active.
- Date arguments are validated to `YYYY-MM-DD` before any write is attempted.
- Duplicate inserts fail gracefully with a clear message instead of crashing.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

MIT

