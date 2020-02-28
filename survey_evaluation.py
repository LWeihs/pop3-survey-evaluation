#!/usr/bin/env python

import email, poplib
from email.header import decode_header
from bs4 import BeautifulSoup
import re
import argparse
import sys
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.backends.backend_pdf import PdfPages

#set up script params
desc = ('Get evaluation data from your mail server and writes results to a '
    'file as well as plotted results to pdf files. If you do not need one of '
    'these file types, set -notxt, -nobar, -nopie flags as desired. If your '
    'mail server is not web.de or your subject is no longer "Evaluation", '
    'make sure to set --pop_server and --subject to fitting values.')
parser = argparse.ArgumentParser(description=desc)
parser.add_argument('login', type=str, help='Your email login')
parser.add_argument('password', type=str,
                    help='The password for your email account')
parser.add_argument('--pop_server', type=str,
                    help='The POP3 server address of your mail server')
parser.add_argument('--subject', type=str,
                    help='E-Mail subject related to survey mails')
parser.add_argument('-notxt', action='store_true',
                    help='Disable saving of results to txt file')
parser.add_argument('-nobar', action='store_true',
                    help='Disable plotting of bar plots')
parser.add_argument('-nopie', action='store_true',
                    help='Disable plotting of pie plots')
args = parser.parse_args()

#set variables used in script
login = args.login
password = args.password
pop_server = (args.pop_server if args.pop_server else 'pop3.web.de')
filter_subject = (args.subject if args.subject else 'Evaluation')
write_txt = not args.notxt
write_bars = not args.nobar
write_pies = not args.nopie
colors_simple = ['red', 'royalblue']
colors_five = ['red', 'darkorange', 'gold', 'limegreen', 'royalblue']
colors_ten = ['red', 'darkorange', 'gold', 'yellowgreen', 'limegreen',
              'deepskyblue', 'royalblue', 'navy', 'purple', 'darkmagenta']
txt_file_name = 'results.txt'
bar_file_name = 'result_bars.pdf'
pie_file_name = 'result_pies.pdf'

#establish server connection
mail_box = None
try:
    mail_box = poplib.POP3_SSL(pop_server)
    mail_box.user(login)
    mail_box.pass_(password)
except Exception as err:
    print('Login failed:', err)
    exit(1)
print('Connected to mail server...')

#gather results in dict
results = {}
def make_entry(key, val):
    if not key in results:
        results[key] = []
    results[key].append(val)

#fetch data from mails and write progress to stdout
num_messages = len(mail_box.list()[1])
print('Checking mails:')
sys.stdout.write('Done: ')
for i in range(num_messages):
    #notify progress
    done_str = '{}/{}'.format(i+1, num_messages)
    sys.stdout.write(done_str)
    sys.stdout.flush()
    sys.stdout.write('\b' * len(done_str))
    
    #get email html content
    raw_email  = b"\n".join(mail_box.retr(i+1)[1])
    msg = email.message_from_bytes(raw_email)
    subject = decode_header(msg['Subject'])[0][0]
    if (subject != filter_subject):
        continue
    content = msg.get_payload(decode=True)
    content = content.decode('utf-8')
    
    #extract questions and answers from html content
    questions = []
    answers = []
    soup = BeautifulSoup(content, 'html.parser')
    wrap = soup.find(class_='mcnTextContent')
    tds = wrap.find_all('td')
    for answer in tds:
        answer = str(answer.contents[0])
        m = re.search('<strong>(.*)<\/strong>', answer)
        if m:
            questions.append(m.group(1))
        else:
            answers.append(answer)
    q_len = len(questions)
    if (q_len != len(answers)):
        continue
    for i in range(q_len):
        make_entry(questions[i], answers[i])
sys.stdout.write('\033[2K\033[1G')
sys.stdout.write('All done.\n')
sys.stdout.flush()

#transform results to wanted output format
sorted_results = {}
for question, answers in results.items():
    counts = {}
    for answer in answers:
        if not answer in counts:
            counts[answer] = 1
        else:
            counts[answer] += 1
    sorted_answers = sorted(counts.items(), key=lambda kv: kv[1],
                           reverse = True)
    sorted_results[question] = sorted_answers

#prepare writing to txt file
def write_qa(res_file, question, sorted_counts):
    res_file.write('Frage: {}\n'.format(question))
    res_file.write('Antworten:\n')
    for answer, times in sorted_counts:
        res_file.write('\t{} (x{})\n'.format(answer, times))
    res_file.write('\n')
    
#prepare plotting
def get_colors(nr_answers):
    if nr_answers <= 2:
        return colors_simple
    elif nr_answers <= 5:
        return colors_five
    else:
        return colors_ten
    
def plot_bars(question, ratings, labels):
    nr_answers = len(labels)
    x = [i for i in range(nr_answers)]
    fig, axis = plt.subplots()
    axis.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    plt.bar(x, ratings, color=get_colors(nr_answers))
    plt.xticks(x, labels)
    plt.title(question)
    plt.tight_layout
    pass
    
def plot_pie(question, ratings, labels):
    plt.pie(ratings, labels=labels, colors=get_colors(len(labels)))
    plt.title(question)
    plt.tight_layout
    pass

def start_write_plot_to_pdf():
    plt.figure()

def end_write_plot_to_pdf(pdf):
    pdf.savefig() # saves the current figure into a single pdf page
    plt.close()

#write questions + answers to simple .txt file if so desired
if write_txt:
    with open(txt_file_name, 'w') as res_file:
        print('Writing results to {}...'.format(res_file.name))
        for question, sorted_answers in sorted_results.items():
            write_qa(res_file, question, sorted_answers)
        print('Done.')
    
#create bar graph pdf file if so desired
if write_bars:
    with PdfPages(bar_file_name) as pdf:
        print('Creating bar plots in file {}...'.format(bar_file_name))
        for question, sorted_answers in sorted_results.items():
            labels = [label[0] for label in sorted_answers]
            ratings = [label[1] for label in sorted_answers]
            start_write_plot_to_pdf()
            plot_bars(question, ratings, labels)
            end_write_plot_to_pdf(pdf)
        print('Done.')
        
        
#create pie graph pdf file if so desired
if write_pies:
    with PdfPages(pie_file_name) as pdf:
        print('Creating pie plots in file {}...'.format(pie_file_name))
        for question, sorted_answers in sorted_results.items():
            labels = [label[0] for label in sorted_answers]
            ratings = [label[1] for label in sorted_answers]
            start_write_plot_to_pdf()
            plot_pie(question, ratings, labels)
            end_write_plot_to_pdf(pdf)
        print('Done.')

#close open connection, finish up
mail_box.quit()
print('All done. Exit.')
