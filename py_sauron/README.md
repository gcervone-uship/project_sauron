# Py_Sauron

The goal behind py_sauron is to provide a framework for reducing the time to required to implement additional functionality for the unified pipeline. It breaks everything down into small, testable, components, and seperates the program logic from the various operations to be performed.

## Primitives

The 2 fundamental classes implemented are the `Item` class and the `Result` class. All plugins consume or emit these objects, and all program logic acts upon these objects

### Item Class

The main attributes of an item are:
  * Key
  * Value
  * Prefix
  
There is a `clone` method that can be used to return a new Item object with new attributes.

Items have the required attributes for things like sorting and comparisons 

### Result Class

The main attributes of a Result are:
  * result
  * invalid
  * output

These attributes should either be an Item, or a list/iterable of items.

There are also the following attributes that can be used as well:
  * exception
  * raw
  * retry
  
  
Output is useful for collecting things like the serialized text to be written to a file, it should generally be text of some form.
Raw is ambiguious, it is generally just for debugging purposes for things like raw response items.
Exception is useful for collecting exceptions encountered. By wrapping them, we can wrap additional logic around invalid items
Retry Indicates of invalid items can be retried. 

## Plugins

Plugins are the fundamental way of interacting with the world. These can be ways of reading in from different sources, or writing out items.

Current plugins are:
  * Consul
  * Cloudformation Templates
  * Cloudformation Stacks
  
## Operations
  
### `join_prefix`
Takes an item, and optionally a seperator, The prefix is joined with the key with an optional seperator

### `split_prefix`
Takes an item, a prefix and optionally a seperator. Effectively the opposite of `join_prefix`

### `split_by_sep`
Takes an item with an empty prefix, and a seperator, and generates a prefix.
If the seperator is repeated, only use the final section as the key, the rest will be joined back together with the seperator to form the prefix.
For example, this is useful for operating on consul paths. It would turn a key of `dev/example-stack/example-key` into a key of `example-key` and a prefix of `dev/example-stack`

### `new_prefix`
Takes an item and a prefix, and returns a new item with the given prefix

### `drop_prefix`
Takes an item, and returns a new item without a prefix

### `drop_value`
Takes an item, and returns a new item without a key

### `get_by_prefix`
Takes a list of items, and returns a result object with a `result` of the items with a matching prefix, and an `invalid` of the items that don't match the prefix

### `dedup_items`
Removes duplicate items. It only accounts for the key, value, and prefix. Any other attributes are ignored

### `dedup_prefix_keys`
Finds items with overlapping key/value pairs for each prefix

### `fill_values`
Takes 2 lists of items, a `required_items` list, and a `source_items` list. The source items list will fill values into the required items list. Any values set in required items effectively act as the default values for the result. By default it will raise an exception if there are any values that aren't filled.
  
### `make_valid`
Accepts an item[s] Make a result object with those in the result attribute

### `make_invalid`
Accepts an item[s] Make a result object with those in the invalid attribute

### `item_action`
Takes a list of items, and a list of functions. The list of functions effectively acts as a pipeline. If a result object is encountered, it will apply the action on its `.result`, if it encounters an Item, it will apply the function to the item, otherwise, it will just return the given item unchanged

### `action_on_result`
Takes a function and an object. If a result object is encountered, it will apply the action on its `.result`, if it encounters an Item, it will apply the function to the item, otherwise, it will just return the given item unchanged.

### inspector
Takes an item, prints the item, and returns the item. Useful for debugging

### operate
Its simply `list()`, but it helps communicate intention. Lots of operations evaluate lazily, so actions don't happen until they are consumed. We use list or operate to ensure that everything has been consumed, and all actions have been performed.
