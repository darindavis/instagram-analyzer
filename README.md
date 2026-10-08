# instagram-analyzer
This is a case study in integrating Python (data preparation) with Power BI (visualization) to build a high granularity date/time hierarchy.

The ultimate product is an analytical dashboard in Power BI which answers questions such as:

- Who exchanged messages?
- How many messages were sent by whom?
- What was the distribution of messages over time?
- Were messages sent during a blackout period?
- What was the average time gap between messages?

Combine the data transformation of Python with the visualization of Power BI to build an interactive analytical dashboard capable of drilling down from year to minute granularity. This case study illustrates numerous Python techniques: series vs dataframes, JSON parsing, join/group/map tables, nested and lambda functions, loop avoidance, efficiency considerations. Avoid a “gotcha” when running Python from Power BI. Use a Power BI field parameter to build a drill-down hierarchy of sparse time-series data from multiple tables.

[Video walk-through](https://youtu.be/EB8Rjd6IOOA)