# How to Run OUTFIT.exe

**Repository:** [ParaGroup/OUTFIT](https://github.com/ParaGroup/OUTFIT)

## 1. Download & Extract
- Download [OUTFIT.zip](https://github.com/ParaGroup/OUTFIT/raw/refs/heads/main/OUTFIT.zip)
- Unzip the file


## 2. Prepare Data
- Get the `city.csv` file from the repo’s `data` folder (or your own GIS data)
- Place `city.csv` in the same folder as `OUTFIT.exe`

## 3. Run the App
- Double-click `OUTFIT.exe`
- If Windows blocks it:
  - Click **More Info**

		![](WindowsSmartScreen-1.png)

  - Then click **Run Anyway**

  		![](WindowsSmartScreen-2.png)

## 4. Fill Required Fields
- **API Key** → your Google API key
- **Prefix** → name to identify your dataset
- **Data** → path to `city.csv`
- **Date Range** → time span for data collection
- **Interval** → minutes between API calls

![](OUTFIT.png)

## 5. Start & Verify
- Click **Start Schedule** button → you’ll see *“Task Scheduled!”*

	![](TaskScheduled.png)

- Open **Task Scheduler Configuration Tool** (**Utilita' di Pianificazione**) to confirm the task has been created!

	(The task will be named with the prefix "**outfit_**")

	![](TaskSchedulerConfigurationTool.png)