#!/bin/python

import os
import re
import json
import shutil
import subprocess

import requests as r

rich_hickey_image_link = 'https://i.imgflip.com/411lb0.png'

def shadow_config(reagent_version, namespace):
    return '''\
{:source-paths
 ["src/main"]

 :dependencies
 [[reagent "''' + reagent_version + '''"]]

 :builds
 {:app
  {:target :react-native
   :init-fn ''' + namespace + '''.core/init
   :output-dir "app"
   :js-options {:js-package-dirs ["node_modules"]}}}}
'''

def core_src(project_name, namespace):
    return '''\
(ns ''' + namespace + '''.core
  (:require
    ["react-native" :as rn :refer [AppRegistry]]
    [reagent.core :as r]))

(defn app-root []
  (let [show-react-logo (r/atom true)]
   (fn []
     (js/setTimeout #(swap! show-react-logo not) 1000)
     [:> rn/View {:style {:flex 1
                          :justify-content :center
                          :align-items :center}}
      [:> rn/Text {:style {:font-size 40
                           :text-align :center}}
       "Welcome to\nClojure\napp development"]
      [:> rn/View {:style {:flex-direction :row}}
       [:> rn/Image {:source (js/require "../assets/hickey.png")
                     :style {:width 100 :height 100}}]
         [:> rn/Image {:source {:uri (if @show-react-logo
                                       "https://reactnative.dev/img/tiny_logo.png"
                                       "https://upload.wikimedia.org/wikipedia/commons/8/85/Clojure-icon.png")}
                       :style {:width 50 :height 50}}]]])))

(defn start []
  (.registerComponent AppRegistry
                      "''' + project_name + '''"
                      #(r/reactify-component app-root)))

(defn ^:export init []
  (start))
'''

def get_newest_reagent_version():
    resp = r.get('https://clojars.org/api/artifacts/reagent/reagent')
    if resp.status_code != 200:
        print('Could not fetch newest reagent version')
        return '1.1.1'
    version =  resp.json()['latest_version']
    print(f'Newest reagent version is {version}')
    return version

def make_snake_case(name):
    # stolen from https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

def main():
    if shutil.which('npx') is None:
        print('npx not in path. Did you install npm correctly?')

    if shutil.which('npm') is None:
        print('npm not in path. Did you install npm correctly?')

    print('If you haven\' already, please setup your environment')
    print('Just follow this guide: https://reactnative.dev/docs/environment-setup')
    project_name = input('Project Name: ')
    if not os.path.isdir(project_name):
        subprocess.run(['npx', 'react-native', 'init', project_name])
    else:
        print(f'There seems to be a project named {project_name} already')
        choice = input('Do you want only run the transformation steps? THIS WILL OVERWRITE YOUR CODE [y/N] ')
        if choice != 'y':
            return

    os.chdir(project_name)
    snake_project_name = make_snake_case(project_name)
    namespace = re.sub('_', '-', snake_project_name)

    # # add shadow-cljs to compile and watch the clojurescript code
    subprocess.run(['npm', 'install', '--save-dev', 'shadow-cljs'])

    # # remove js test/lint packages since the programming will be done in clojure
    subprocess.run(['npm', 'uninstall', '--save-dev', 'babel-jest', 'eslint', 'jest'])

    with open('package.json', 'r') as package:
        content = json.load(package)
        if 'jest' in content:
            del content['jest']
        if 'scripts' in content:
            if 'test' in content['scripts']:
                del content['scripts']['test']
            if 'lint' in content['scripts']:
                del content['scripts']['lint']
        else:
            content['scripts'] = {}

    with open('package.json', 'w') as package:
        json.dump(content, package, indent=2)

    # metro injects facebook trackers into your app
    if os.path.isfile('metro.config.js'):
        os.remove('metro.config.js')
    if os.path.isdir('__tests__'):
        shutil.rmtree('__tests__')

    with open('shadow-cljs.edn', 'w') as shadow:
        shadow.write(shadow_config(get_newest_reagent_version(), namespace))

    src_path = f'src/main/{snake_project_name}'
    if not os.path.exists(src_path):
        os.makedirs(src_path)

    with open(f'{src_path}/core.cljs', 'w') as core:
        core.write(core_src(project_name, namespace))

    with open('index.js', 'w') as index:
        index.write('import \'./app/index.js\';')

    if not os.path.exists('assets'):
        os.makedirs('assets')

    if not os.path.exists('assets/hickey.png'):
        resp = r.get(rich_hickey_image_link, allow_redirects=True)
        if resp.status_code == 200:
            with open('assets/hickey.png', 'wb') as hickey:
                hickey.write(resp.content)

    print('Running the app:')
    print('First start an android/ios emulator')
    print('e.g. for android: https://developer.android.com/studio/run/managing-avds')
    print('----')

    print('Then open 2 additional terminals and run the following commands in those')
    print('First terminal:')
    print('  # this will watch for changes in your clojure code and automatically update your js accordingly')
    print(f'  cd {project_name} && npx shadow-cljs watch app')
    print('Second Terminal:')
    print('  # this will watch for changes in your generated js code and automatically reload the app if something changed')
    print('  # any prn/println calls will be displayed here!')
    print(f'  cd {project_name} && npm start')
    print('Third Terminal:')
    print('  # this will install and start your app inside your emulator')
    print(f'  cd {project_name} && npm run android')
    print('----')

    print('If you did everything correctly you should now see a nice little example app in your emulator')
    print(f'The code for that demo is located in {project_name}/src/main/{namespace}/core.cljs')
    print('if you change any part of the code the app should update automatically')
    print('----')
    print('One more tip: Sometimes react native apps will crash while reloading.')
    print('In that case you can just restart the app in android and press `r` in the second terminal (npm start)')


if __name__ == '__main__':
    main()
