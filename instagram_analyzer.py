#!/usr/bin/env python
# coding: utf-8

# # Instagram Analyzer
# History: 9/29/26 Initial version
# 
# Answer questions:
# - Who exchanged messages
# - How many messages per person
# - Distribution of messages during day
# - Messages sent during blackout periods
# 
# Source: Export from Instagram all content as JSON. Extract zip file
# - File/folder structure:
# - Top level folder: your_instagram_activity\messages\inbox
# - Subfolders: one per correspondent. Contains message_1.json, photos folder, videos folder

# # Imports

# In[145]:


import sys # need for debug()
from pathlib import Path
import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns


# # Variables

# In[146]:


top_folder = Path("/Temp/your_instagram_activity/messages/inbox")


# # Functions

# In[147]:


def debug(msg=""):
    debug_flag = False

    if debug_flag:
        frame = sys._getframe(1) # 1 = caller's frame
        line = frame.f_lineno # 1 = caller's line number
        func_name = frame.f_code.co_name # function name of caller
        # print(f"DEBUG [{__file__}:{line}] {msg}")
        print(f"DEBUG [{func_name}:{line}] {msg}")


# # load_jsons_to_df()
# Find all the JSON files and combine them into a single dataframe

# In[148]:


def load_jsons_to_df(top_folder: Path) -> pd.DataFrame:
    paths = list(top_folder.rglob("message_*.json"))

    frames = [] # initialize list of dataframes (one per JSON file)
    
    for path in paths:
        # ASSERT: path = \Temp\your_instagram_activity\messages\inbox\instagramuser_1007385998787130\message_1.json
        
        folder_name = path.parent.name # isolate the folder name of this file
        # ASSERT: folder_name = instagramuser_1007385998787130

        username = folder_name.rsplit("_", 1)[0] # split from the right on "_" at most 1 time; select the 0th element of the resulting list
        # ASSERT: username = instagramuser
        
        with path.open(encoding="utf-8") as f:
            json_data = json.load(f)
            # ASSERT: json_data is a dictionary containing the JSON from the file

        
        messages_list = json_data.get("messages", []) # return the messages value (a list of dictionaries) or an empty list
        # ASSERT: messages is a list of message dictionaries
        if not messages_list: # check next path if this path has no messages
            continue
        df = pd.json_normalize(messages_list) # convert each message dictionary into a row where the key is a column

 
        participants_list = json_data.get("participants", []) # return the participants value (a list of dictionaries) or an empty list
        # ASSERT: participants_list is a list of participant dictionaries
        if not participants_list: # check next path if this path has no participants
            continue
        participants_df = pd.json_normalize(participants_list) # convert each participant dictionary into a row where the key is a column

        
        df["thread_username"] = username
        df["thread_title"] = json_data.get("title")
        df["thread_path"] = json_data.get("thread_path")
        df["_source_file"] = path.name
        df["_source_folder"] = str(path.parent)
        df["timestamp"] = (
            pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True)
            .dt.tz_convert("America/New_York")
        )

        # identify the name which is NOT the title
        principal_df = participants_df.loc[participants_df["name"] != df['thread_title'].iloc[0], "name"]
        # print("\nprincipal_df:\n", principal_df) # debug
        df["principal"] = principal_df.iloc[0] if not principal_df.empty else pd.NA # save the name of the principal
        # print("\ndf[principal]:\n", df["principal"]) # debug

        frames.append(df)
        # print(username, path.name, len(df))

    if not frames: # if didn't find any JSON files
        return pd.DataFrame() # return empty dataframe

    return pd.concat(frames, ignore_index=True) # discard existing indexes and index (0-base) the combined rows from scratch


# # Add month column

# In[149]:


def add_month_column(df) -> pd.DataFrame:
    df["month"] = (
        df["timestamp"]
        .dt.tz_localize(None) # remove timezone to prevent compiler warning about dropping timezone
        .dt.to_period("M") # identify the YYYY-MM of the timezone
        .astype(str) # treat month as a string
    )
    return df


# # Add day column

# In[150]:


def add_day_column(df) -> pd.DataFrame:
    df["day"] = (
        df["timestamp"]
        .dt.tz_localize(None) # remove timezone to prevent compiler warning about dropping timezone
        .dt.to_period("D") # identify the YYYY-MM-DD of the timezone
        .astype(str) # treat day as a string
    )
    return df


# # Add hour column

# In[151]:


def add_hour_column(df) -> pd.DataFrame:
    df["hour"] = (
        df["timestamp"]
        .dt.tz_localize(None) # remove timezone to prevent compiler warning about dropping timezone
        .dt.to_period("h") # identify the YYYY-MM-DD HH:00 of the timezone
        .astype(str) # treat hour as a string
    )
    return df


# # Add weekday column

# In[152]:


def add_weekday_column(df) -> pd.DataFrame:
    df["weekday"] = (
        df["timestamp"]
        # .dt.tz_localize(None) # remove timezone to prevent compiler warning about dropping timezone
        .dt.day_name() # identify the weekday name
        # .astype(str) # treat hour as a string
    )
    return df


# # Add timegap column
# Gap is the difference (in minutes) between the timestamps of two consecutive messages

# In[153]:


def add_timegap_column(df) -> pd.DataFrame:
    df = df.sort_values("timestamp").reset_index(drop=True) # rebuild the index and discard the old index (instead of saving it as a column)
    df["timegap"] = df["timestamp"].diff().dt.total_seconds() / 60 # compute gaps between timestamps expressed in minutes
    # total_seconds() / 60 keeps fractional minutes; use total_seconds() // 60 or .round() for whole minutes
    return df


# # Add class to blackout
# Create a dataframe for one class and append it to the received dataframe

# In[154]:


def add_class(rows_list, class_name, weekday, start, stop): # returns nothing
    # list accumulation by modifying variable 'rows_list'
    rows_list.append(
        {
            "class": class_name,
            "weekday": weekday,
            "start": start,
            "stop": stop,
        }
    )
    # no return required because the list 'rows_list' is a mutable object passed by reference


# In[155]:


# NOT USED - INITIAL SOLUTION KEPT FOR COMPARISON
def concat_class(df, class_name, weekday, start, stop) -> pd.DataFrame:
    # debug("\n\nconcat_class()\n\n")
    new_row = pd.DataFrame(
        {
            "class": [class_name],
            "weekday": [weekday],
            "start": [start],
            "stop": [stop],
        }
    )
    return pd.concat([df, new_row], ignore_index=True) # inefficient to allocate dataframe and copy all existing rows


# # Add blackout column
# Flag messages sent during blackout periods

# In[156]:


def add_blackout_column(df) -> pd.DataFrame:
    # debug("\n\nadd_blackout_column()\n\n")
    # build blackout dataframe

    blackout_list = [] # initilize to blank list

    add_class(blackout_list, "class1", "Monday", "20:00", "21:00")
    
    add_class(blackout_list, "class2a", "Monday", "14:40", "16:10")
    add_class(blackout_list, "class2b", "Wednesday", "14:40", "16:10")
    
    add_class(blackout_list, "class3a", "Tuesday", "14:40", "16:10")
    add_class(blackout_list, "class3b", "Thursday", "14:40", "16:10")
    
    add_class(blackout_list, "class4a", "Tuesday", "09:40", "11:10")
    add_class(blackout_list, "class4b", "Thursday", "09:40", "11:10")

    add_class(blackout_list, "class5a", "Monday", "11:20", "12:50")
    add_class(blackout_list, "class5b", "Wednesday", "11:20", "12:50")

    add_class(blackout_list, "class6a", "Monday", "13:00", "14:30")
    add_class(blackout_list, "class6b", "Wednesday", "13:00", "14:30")

    # print(blackout_list) # debug

    blackout_df = pd.DataFrame(blackout_list)
    # print(blackout_df) # debug

    # convert start and stop from strings to datetime
    blackout_df["start_t"] = pd.to_datetime(blackout_df["start"], format="%H:%M").dt.time
    blackout_df["stop_t"] = pd.to_datetime(blackout_df["stop"], format="%H:%M").dt.time
    # print(blackout_df) # debug

    events_df = df.copy() # work on a copy just to be safe; focus is on the time of the message as an "event"
    events_df["_time"] = pd.to_datetime(events_df["timestamp"]).dt.time # isolate the time portion of this event's timestamp
    events_df["_idx"] = events_df.index # save original events_df index so that copies can be grouped back together after the join (merge)

    events_joined_with_blackout = events_df.merge( # left join events with blackout
        blackout_df[["class", "weekday", "start_t", "stop_t"]], # add the class, start_t and stop_t columns from blackout to events
        on="weekday",
        how="left",
    )
    # ASSERT: rows from events_df will be duplicated for each matching weekday in blackout_df
    # debug("\n\nevents_joined_with_blackout:\n")
    # print(events_joined_with_blackout.filter(['thread_username', 'timestamp', 'weekday', '_time', 'start_t', 'stop_t']).head()) # debug

    
    in_window = ( # keep only the rows that match the weekday and occur between the start and stop times
        events_joined_with_blackout["start_t"].notna()
        & (events_joined_with_blackout["_time"] >= events_joined_with_blackout["start_t"])
        & (events_joined_with_blackout["_time"] <= events_joined_with_blackout["stop_t"])
    )
    # ASSERT: series whose values are booleans and index is aligned with events_joined_with_blackout
    
    # debug("\n\nin_window (series):\n")
    # print(in_window.head()) # debug

    # solution 1
    # events_df["blackout"] = ( # define boolean for each event
    #     in_window
    #     .groupby(events_joined_with_blackout["_idx"]) # bundle every merged event row that came from the same original event
    #     .any() # an event is a blackout if any of its windows matches
    #         # ASSERT: result is a Series indexed by original event index (_idx)
    #     .reindex(events_df.index, fill_value=False) # put the series back in events_df order and length
    #         # if none of the copies of an event matched a window, fill that event's blackout with False
    # )

    # solution 2
    matched = events_joined_with_blackout.loc[in_window, ["_idx", "class"]] # in_window is treated as a boolean mask, not a list of labels
    # ASSERT: matched is a dataframe containing two columns ("_idx", "class") and only the True rows (from in_window)
    
    class_by_idx = matched.groupby("_idx")["class"].first() # remove any duplicate rows (just to be certain)
    # ASSERT: class_by_idx is a series, index is the original "_idx", values are the class names
    
    events_df["class"] = events_df["_idx"].map(class_by_idx) # look up each event’s _idx in class_by_idx; found > class name; not found > NaN
    
    events_df["blackout"] = events_df["class"].notna() # if there's a class name, event occurred during blackout (True)
    
    events_df = events_df.drop(columns=["_time", "_idx"]) # no longer need these temp columns

    return events_df


# # Anonymize
# Anonymize user identifiable data

# In[157]:


def anonymize(df) -> pd.DataFrame:
    debug("anonymize()")

    def canon(name): # return the canonical name for an alias
        if pd.isna(name):
            return name
        return aliases_dict.get(name, name) # utilize dictionary in enclosing scope
    
    pairs_df = ( # create dataframe with just the thread_title and thread_username columns
        df[["thread_title", "thread_username"]]
        .dropna()
        .drop_duplicates()
    )
    # print("\npairs_df:\n", pairs_df) # debug
    # ASSERT: principal is NOT in pairs_df
    
    # create a dictionary of aliases to equate thread_title with thread_username
    aliases_dict = dict(zip(pairs_df["thread_title"], pairs_df["thread_username"]))
    # aliases_dict = pairs_df.set_index("thread_title")["thread_username"].to_dict() # another way to do it
    # print("\naliases_dict\n:", aliases_dict) # debug

    # canonicalize names across columns (one version of the truth)
    for col in ["thread_username", "principal", "sender_name", "thread_title"]:
        df[col] = df[col].map(canon) # calls canon() with the current value of col as the name argument
    
    unique_names_list = (df["thread_username"] # get list of unique usernames not including the principal
        .dropna() # ignore missing values
        .unique() # .unique() returns a NumPy ndarray
        .tolist() # convert to list
    )
    # print("\nunique_names_list:\n", unique_names_list) # debug
    # print(type(unique_names_list)) # debug

    principal = df["principal"].dropna().iloc[0] # get name of principal
    # unique_names_list.append(principal) # add principal to list of unique names
    
    # create map of thread_username > generic name using a dictionary comprehension
    anon_map = {thread_username: f"user{i}" for i, thread_username in enumerate(unique_names_list, start=1)}
    # ASSERT: values dictionary = {'tom': 'user1', 'dick': 'user2', 'harry': 'user3' ... }
    anon_map[principal] = "principal"
    # print("\nanon_map:\n", anon_map) # debug

    # replace the real names with generic names
    df["principal"] = df["principal"].map(anon_map)
    df["sender_name"] = df["sender_name"].map(anon_map)
    df["thread_title"] = df["thread_title"].map(anon_map)
    df["thread_username"] = df["thread_username"].map(anon_map)

    df["content"] = df.index.map(lambda i: f"message {i}") # anonymous function with argument i, executed for every row index
    df["reactions"] = df.index.map(lambda i: f"reaction {i}")

    return df


# # Plot Message Counts by User

# In[158]:


def plot_msg_count_by_user(df):
    debug("plot_msg_count_by_user()")
    
    first_date = df['timestamp'].min()
    last_date = df['timestamp'].max()
    # print("\nFrom", first_date, "to", last_date, "\n")
    
    counts_df = (
        df.groupby("thread_username") # split the DataFrame into groups, one group per distinct thread_username
        .size() # create series of message counts per thread_username
        .reset_index(name="n_messages") # create dataframe with index, thread_username and n_messages columns
        .sort_values("n_messages", ascending=False)
    )

    plt.figure(figsize=(12, 5))
    sns.barplot(data=counts_df, x="thread_username", y="n_messages")
    plt.xticks(rotation=90)
    plt.xlabel("Usernames")
    plt.ylabel("Number of Messages")
    plt.title("Messages per Username")
    plt.tight_layout()
    plt.show()


# # Show Top 5 by Month

# In[159]:


def show_top_5_by_month(df):
    debug("show_top_5_by_month()")
    
    # limit analyze to messages in the previous 6 months
    # end = pd.Timestamp.now(tz="America/New_York")
    # start = (end - pd.DateOffset(months=6)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # df = df.loc[df["timestamp"] >= start].copy()
    
    counts_by_month = (
        df.groupby(["month", "thread_username"])
        .size() # returns a series with 2 index levels ("month" and "thread_username"), values = count of rows
        .reset_index(name="n_messages") # create a new 0-base index, prev index levels become columns, values become a column named "n_messages"
    )
    debug(f"\n\ncounts_by_month shape: {counts_by_month.shape} \n\n")
    # debug(counts_by_month.info())
    
    top5 = (
        counts_by_month.sort_values(["month", "n_messages"], ascending=[True, False])
        .groupby("month", group_keys=False)
        .head(5)
    )
    
    plt.figure(figsize=(12, 6))
    sns.barplot(
        data=top5,
        x="month",
        y="n_messages",
        hue="thread_username",
    )
    plt.ylabel("Messages")
    plt.xlabel("Month")
    plt.title("Top 5 threads by message count, past 6 months")
    plt.legend(title="thread_username", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.show()


# # Main Code

# In[160]:


def main():
    global msgs_df # create in namespace that Power BI can see
    msgs_df = load_jsons_to_df(top_folder)
    # print(msgs_df.shape, "\n\n")
    # print(msgs_df.info(), "\n\n")
    # print(msgs_df.head())
    pd.set_option("display.expand_frame_repr", False)
    # pd.set_option("display.max_colwidth", None)   # don't truncate cell text
    # pd.set_option("display.width", None)          # use the full terminal width
    # print(msgs_df.filter(['thread_username', 'sender_name', 'timestamp', 'content']).head())

    # delete unneeded columns before any further processing
    msgs_df.drop(columns=["photos", "videos", "audio_files", "share.link", "share.share_text",
                          # "content", "reactions",
                          "share.original_content_owner", "share.profile_share_username", "share.profile_share_name",
                         "is_geoblocked_for_viewer", "is_unsent_image_by_messenger_kid_parent",
                         "thread_path", "_source_folder"], inplace=True)
    
    msgs_df = add_month_column(msgs_df)
    msgs_df = add_day_column(msgs_df)
    msgs_df = add_hour_column(msgs_df)
    msgs_df = add_weekday_column(msgs_df)
    msgs_df = add_timegap_column(msgs_df)
    msgs_df = add_blackout_column(msgs_df)
    # print(msgs_df.info()) # debug
    # print(msgs_df.filter(['thread_username', 'sender_name', 'principal', 'timestamp', 'weekday', 'blackout', 'content']).head()) # debug
    # print("\nafter adding blackout_column:\n", msgs_df.query("blackout == True")
    #       .filter(['thread_username', 'thread_title', 'sender_name', 'principal', 'timestamp', 'weekday', 'blackout', 'class'])) # debug


    msgs_df = anonymize(msgs_df)
    # print("\nafter anonymize():\n", msgs_df.filter(['thread_username', 'sender_name', 'principal', 'timestamp', 'weekday', 'blackout', 'content', 'reactions']).head()) # debug
    # print("\nafter anonymize():\n", msgs_df.query("blackout == True")
    #       .filter(['thread_username', 'thread_title', 'sender_name', 'principal', 'timestamp', 'weekday', 'blackout', 'class'])) # debug

    # print(msgs_df.info(), "\n\n")

    # plot_msg_count_by_user(msgs_df)
    # show_top_5_by_month(msgs_df)
       
if __name__ == "__main__":
    main()