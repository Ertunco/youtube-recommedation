from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pandas as pd

# YOUTUBE_API_KEY
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

def get_start_date_string(search_period_days):
    """Returns string for date at start of search period."""
    search_start_date = datetime.today() - timedelta(search_period_days)
    date_string = datetime(year=search_start_date.year,month=search_start_date.month,
                           day=search_start_date.day).strftime('%Y-%m-%dT%H:%M:%SZ')
    return date_string

def search_each_term(search_terms, api_key, uploaded_since,
                        views_threshold=5000, num_to_print=5):
    """Uses search term list to execute API calls and print results."""
    if type(search_terms) == str:
        search_terms = [search_terms]

    list_of_dfs = []
    for index, search_term in enumerate(search_terms):
        df = generate_df(views_threshold, search_terms[index], api_key, uploaded_since)
        df = df.sort_values(['Score'], ascending=[0])
        list_of_dfs.append(df)

    # 1 - concatenate them all
    full_df = pd.concat((list_of_dfs),axis=0)
    full_df = full_df.sort_values(['Score'], ascending=[0])
    print("THE TOP VIDEOS OVERALL ARE:")
    print_top_videos(full_df, num_to_print)
    print("==========================\n")

    # 2 - in total
    for index, search_term in enumerate(search_terms):
        results_df = list_of_dfs[index]
        print("THE TOP VIDEOS FOR SEARCH TERM '{}':".format(search_terms[index]))
        print_top_videos(results_df, num_to_print)

    results_df_dict = dict(zip(search_terms, list_of_dfs))
    results_df_dict['top_videos'] = full_df

    return results_df_dict

def print_top_videos(df, num_to_print):
    """Prints top videos to console, with details and link to video."""
    if len(df) < num_to_print:
        num_to_print = len(df)
    if num_to_print == 0:
        print("No video results found")
    else:
        for i in range(num_to_print):
            video = df.iloc[i]
            title = video['Title']
            views = video['Views']
            subs = video['Subscribers']
            link = video['Video URL']
            print("Video #{}:\nThe video '{}' has {} views, from a channel \
            with {} subscribers and can be viewed here: {}\n"\
                                                    .format(i+1, title, views, subs, link))
            print("==========================\n")

def search_youtube_api(search_terms, api_key, uploaded_since):
    """Executes search through API and returns result."""
    # Initialise API Call
    youtube_api = build(serviceName=YOUTUBE_API_SERVICE_NAME,version=YOUTUBE_API_VERSION,developerKey=api_key)

    # API Search Response
    search_result = youtube_api.search().list(
        q=search_terms,
        part='snippet',
        type='video',
        order='viewCount',
        maxResults=50,
        publishedAfter=uploaded_since
    ).execute()
    return search_result,youtube_api

def how_old(item):
    when_published = item['snippet']['publishedAt']
    when_published_datetime_object = datetime.strptime(when_published,
                                                        '%Y-%m-%dT%H:%M:%SZ')
    today_date = datetime.today()
    days_since_published = int((today_date - when_published_datetime_object).days)
    if days_since_published == 0:
        days_since_published = 1
    return days_since_published

def view_to_sub_ratio(viewcount, num_subscribers):
    if num_subscribers == 0:
        return 0
    else:
        ratio = viewcount / num_subscribers
        return ratio

def custom_score(viewcount, ratio, days_since_published):
    ratio = min(ratio, 5)
    score = (viewcount * ratio) / days_since_published
    return score

def find_title(item):
    """Title of the video"""
    title = item['snippet']['title']
    return title

def find_video_url(item):
    """URL of the video"""
    video_id = item['id']['videoId']
    video_url = "https://www.youtube.com/watch?v=" + video_id
    return video_url

def find_viewcount(item, youtube_api):
    """Number of views for the video"""
    video_id = item['id']['videoId']
    video_statistics = youtube_api.videos().list(id=video_id, part='statistics').execute()
    viewcount = int(video_statistics['items'][0]['statistics']['viewCount'])
    return viewcount

def find_channel_id(item):
    """Channel Id of the channel that published the video"""
    channel_id = item['snippet']['channelId']
    return channel_id

def find_channel_url(item):
    """Channel Url of the channel that published the video"""
    channel_id = item['snippet']['channelId']
    channel_url = "https://www.youtube.com/channel/" + channel_id
    return channel_url

def find_channel_title(item):
    """Channel Title of the channel that published the video"""
    channel_name = item['snippet']['channelTitle']
    return channel_name

def find_num_subscribers(item, channel_id, youtube_api):
    """Channel Subscriber Number of the channel that published the video"""
    subs_search = youtube_api.channels().list(id=channel_id,part='statistics').execute()
    if subs_search['items'][0]['statistics']['hiddenSubscriberCount']:
        num_subscribers = 1000000
    else:
        num_subscribers = int(subs_search['items'][0]['statistics']['subscriberCount'])
    return num_subscribers

def generate_df(views_threshold, search_terms, api_key, uploaded_since):
    """Extracts relevant information and puts into dataframe"""
    # Loop over search results and add key information to dataframe
    search_result,youtube_api = search_youtube_api(search_terms, api_key, uploaded_since)
    df = pd.DataFrame(columns=('Title', 'Video URL','Score','Views','Channel Name','Subscribers','Ratio','Channel URL'))
    i = 1
    for item in search_result['items']:
        viewcount = find_viewcount(item, youtube_api)
        if viewcount > views_threshold:
          title = find_title(item)
          video_url = find_video_url(item)
          channel_url = find_channel_url(item)
          channel_id = find_channel_id(item)
          channel_name = find_channel_title(item)
          num_subs = find_num_subscribers(item, channel_id, youtube_api)
          ratio = view_to_sub_ratio(viewcount, num_subs)
          days_since_published = how_old(item)
          score = custom_score(viewcount, ratio, days_since_published)
          df.loc[i] = [title, video_url, score, viewcount, channel_name, num_subs, ratio, channel_url]
        i += 1
    return df

#channel_response = youtube_service.channels().list().execute()