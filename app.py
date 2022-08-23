
import os

import advertools as adv
import pandas as pd
from dash import Dash, dcc, html, callback, Input, Output, State
from jupyter_dash import JupyterDash
from dash.dash_table import DataTable
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.express as px

app = Dash(  # change this to JupyterDash if running within a notebook
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.FLATLY,
                          dbc.icons.BOOTSTRAP])

app.layout = html.Div([
    dbc.Row([
        dbc.Col(lg=1, md=1, sm=1),
        dbc.Col([
            html.Br(),
            html.H1([html.Code('advertools'),  ' SEO Crawler']), html.Br(),
            dbc.Label("Name a folder to store your crawl project's data:"),
            dbc.Input(id='crawl_project',
                      pattern='[a-zA-z]\S{5,}'),
            dbc.Tooltip('starts with a letter, no spaces, > 4 chars. e.g. DOMAIN_YYYY_MM_DD',
                        target='crawl_project'),
            html.Br(),
            dbc.Label('Enter start URL(s):'),
            dbc.Textarea(id='start_urls', rows=4), html.Br(),
            dbc.Tooltip('One or more URLs, one per line', target='start_urls'),
            dbc.Checkbox(id='follow_links',label='Follow links', value=0),
            dbc.Tooltip('Should the crawler follow and crawl links found on pages recursively? Unticking this would crawl in list mode',
                        target='follow_links'), html.Br(),
            dbc.Button(['Advanced options ',
                        html.I(className='bi bi-chevron-expand')],
                       color='light',
                       id='open_collapse'),
            dbc.Collapse([
                html.Br(),
                html.H5(["URL Parameters ",
                         html.I(id='url_param_question',
                                className='bi bi-question-circle')]),
                dbc.Tooltip("""
                While discovering and following links you might want to exclude
                and/or include URLs that contain certain parameters. Enter
                parameters separated by space, e.g.: color price country
                """, target='url_param_question'),
                dbc.Row([
                    dbc.Col([
                        dbc.Label('Exclude:'),
                        dbc.Input(id='exclude_url_params',), html.Br(),
                    ]),
                    dbc.Col([
                        dbc.Label('Include:'),
                        dbc.Input(id='include_url_params',), html.Br(),
                    ])
                ]),
                html.H5(["URL Regex ",
                         html.I(id='url_regex_question',
                                className='bi bi-question-circle')]),
                dbc.Tooltip("""
                While discovering and following links you might want to exclude
                and/or include URLs that match a certain regular expression.
                """, target='url_regex_question'),

                dbc.Row([
                    dbc.Col([
                        dbc.Label('Exclude:'),
                        dbc.Input(id='exclude_url_regex',), html.Br(),
                    ]),
                    dbc.Col([
                        dbc.Label('Include:'),
                        dbc.Input(id='include_url_regex',), html.Br(),
                    ])
                ]),
                dbc.Label('User-agent:'),
                dbc.Input(id='USER_AGENT'), html.Br(),
                dbc.Label('Maximum pages to crawl:'),
                dbc.Input(id='CLOSESPIDER_PAGECOUNT', inputmode='numeric',
                          pattern='\d+'),
            ], is_open=False, id='advanced_options'), html.Br(), html.Br(),
            dbc.Button('Start', id='crawl_start_button'), 
            dcc.Loading([
                html.Div(id='crawl_status'),
            ]), html.Div([html.Br()] * 20),
        ], lg=6),
        dbc.Col(lg=1),
    ])
])


@callback(
    Output('crawl_status', 'children'),
    Input('crawl_start_button', 'n_clicks'),
    State('crawl_project', 'value'),
    State('start_urls', 'value'),
    State('follow_links', 'value'),
    State('USER_AGENT', 'value'),
    State('CLOSESPIDER_PAGECOUNT', 'value'),
    State('exclude_url_params', 'value'),
    State('include_url_params', 'value'),
    State('exclude_url_regex', 'value'),
    State('include_url_regex', 'value'))
def start_crawling(
    n_clicks, crawl_project, start_urls,
    follow_links, USER_AGENT, CLOSESPIDER_PAGECOUNT, 
    exclude_url_params, include_url_params, exclude_url_regex,
    include_url_regex):
    if not n_clicks or not start_urls or not crawl_project:
        raise PreventUpdate
    try:
        os.mkdir(crawl_project)
    except FileExistsError:
        return html.Br(), html.Br(), html.Div([
            """Seems this folder already exists. Either move it, or select
            a different name"""
        ])
    url_list = [x.strip() for x in start_urls.splitlines()]
    if exclude_url_params is not None:
        exclude_url_params = exclude_url_params.split()
    if include_url_params is not None:
        include_url_params = include_url_params.split()

    adv.crawl(
        url_list,
        f'{crawl_project}/crawl.jl',
        follow_links=bool(follow_links),
        exclude_url_params=exclude_url_params,
        include_url_params=include_url_params,
        exclude_url_regex=exclude_url_regex,
        include_url_regex=include_url_regex,
        custom_settings={
            'JOBDIR': f'{crawl_project}/crawl_job.jl',
            'LOG_FILE': f'{crawl_project}/crawl_logs.log',
            'USER_AGENT': USER_AGENT or adv.spider.user_agent,
            'CLOSESPIDER_PAGECOUNT': CLOSESPIDER_PAGECOUNT or 0,
        })
    crawl_df = pd.read_json(f'{crawl_project}/crawl.jl', lines=True)
    return html.Div([
        html.Br(),
        html.H2("Crawl dataset (sample rows):"), html.Br(),
        dbc.Button('Export', id='export_button'), html.Br(), html.Br(),
        dcc.Download(id="download_crawldf"),
        DataTable(
            data=crawl_df.head(50).astype(str).to_dict('records'),
            columns=[{"name": i, "id": i} for i in crawl_df.columns],
            fixed_rows={'headers': True},
             style_header={
                 'fontFamily': 'Arial',
                 'fontColor': '#2F3B4C',
                 'fontWeight': 'bold'},
            style_data={'fontFamily': 'Arial'},
            style_cell={
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'maxWidth': 200})
    ])


@callback(Output('download_crawldf', 'data'),
          State('crawl_project', 'value'),
          Input('export_button', 'n_clicks'),
          prevent_initial_call=True)
def export_crawl_df(crawl_project, n_clicks):
    full_crawl_df = pd.read_json(f'{crawl_project}/crawl.jl', lines=True)
    return dcc.send_data_frame(full_crawl_df.to_excel, f"{crawl_project}.csv", index=False)


@callback(Output('advanced_options', 'is_open'),
              Input('open_collapse', 'n_clicks'),
              State('advanced_options', 'is_open'))
def toggle_collapse(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open


if __name__ == '__main__':
    app.run_server()
