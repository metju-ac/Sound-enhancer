import os
import shutil
import time

from selenium import webdriver

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException

from webdriver_manager.chrome import ChromeDriverManager

from moviepy.editor import VideoFileClip, AudioFileClip

from pydub import AudioSegment


def prepare_dirs() -> None:
    shutil.rmtree("./.tmp", ignore_errors=True)
    os.mkdir("./.tmp")

    try:
        os.mkdir("./results")
    except FileExistsError:
        pass


def get_driver_options() -> Options:
    options = Options()
    options.add_argument("--start-maximized")

    prefs = {"download.default_directory": "/home/metju/Projects/Sound-enhancer/.tmp"}
    options.add_experimental_option("prefs", prefs)

    return options


def wait_for_download() -> None:
    downloading = True
    while downloading:
        time.sleep(1)
        downloading = False

        files = os.listdir("./.tmp")
        for file in files:
            if file.endswith(".crdownload"):
                downloading = True


def download_lecture(link: str) -> None:
    driver_options = get_driver_options()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                              options=driver_options)

    driver.get(link)

    dialog_box = driver.switch_to.alert
    dialog_box.accept()
    print("Lecture downloading started")

    wait_for_download()

    file_name = os.listdir("./.tmp")[0]
    assert file_name.endswith(".mp4")
    os.rename("./.tmp/" + file_name, "./.tmp/lecture.mp4")

    print("Lecture downloading finished")
    driver.quit()


def extract_audio() -> None:
    print("Audio extraction started")
    video = VideoFileClip("./.tmp/lecture.mp4")
    video.audio.write_audiofile("./.tmp/lecture.mp3", verbose=False, logger=None)
    print("Audio extraction finished")

    print("Audio cutting started")
    audio = AudioSegment.from_mp3("./.tmp/lecture.mp3")
    assert audio.duration_seconds <= 59 * 2 * 60

    cut = audio[:59 * 60 * 1000]
    cut.export("./.tmp/cut01.mp3", format="mp3")

    cut = audio[59 * 60 * 1000:]
    cut.export("./.tmp/cut02.mp3", format="mp3")
    print("Audio cutting finished")


def enhance_audio(login: str, password: str, filepath: str) -> None:
    driver_options = get_driver_options()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                              options=driver_options)

    driver.get(r'https://accounts.google.com/signin/v2/identifier?continue=' +
               'https%3A%2F%2Fmail.google.com%2Fmail%2F&service=mail&sacu=1&rip=1' +
               '&flowName=GlifWebSignIn&flowEntry = ServiceLogin')
    driver.implicitly_wait(15)

    driver.find_element("xpath", '//*[@id ="identifierId"]').send_keys(login)
    driver.find_elements("xpath", '//*[@id ="identifierNext"]')[0].click()
    driver.find_element("xpath", '//*[@id ="password"]/div[1]/div / div[1]/input').send_keys(password)
    driver.find_elements("xpath", '//*[@id ="passwordNext"]')[0].click()

    # state: Logged in Google account
    # action: Go to Adobe page
    driver.get("https://podcast.adobe.com/enhance")
    driver.find_element("xpath", "//button[contains(text(),'Sign in')]").click()
    driver.find_element("xpath", "//span[contains(text(),'Continue with Google')]").click()
    driver.find_element("xpath", "//input[@type='file']").send_keys(os.getcwd() + filepath)

    print("Audio enhancing started")
    while True:
        time.sleep(1)
        try:
            driver.find_element("xpath", "//span[contains(text(),'Download')]").click()
            break
        except NoSuchElementException:
            continue

    print("Audio enhancing finished")
    wait_for_download()


def join_audio() -> None:
    print("Audio joining started")
    first = AudioSegment.from_wav("./.tmp/cut01 (enhanced).wav")
    second = AudioSegment.from_wav("./.tmp/cut02 (enhanced).wav")

    joined = first + second
    joined.export("./.tmp/joined.mp3")
    print("Audio joining finished")


def join_audio_and_video(filename: str) -> None:
    print("Audio and video joining started")
    video = VideoFileClip("./.tmp/lecture.mp4")
    audio = AudioFileClip("./.tmp/joined.mp3")

    joined = video.set_audio(audio)
    joined.write_videofile(f"./results/{filename}.mp4", verbose=False, logger=None)
    print("Audio and video joining finished")


def remove_tmp_dir() -> None:
    shutil.rmtree("./.tmp", ignore_errors=True)


if __name__ == '__main__':
    GOOGLE_LOGIN = "FILL IN"
    GOOGLE_PASSWORD = "FILL IN"

    download_link = input("Enter lecture download link:")
    output_file_name = input("Enter output file name (without '.mp4'):")

    prepare_dirs()
    download_lecture(download_link)
    extract_audio()
    enhance_audio(GOOGLE_LOGIN, GOOGLE_PASSWORD, "/.tmp/cut01.mp3")
    enhance_audio(GOOGLE_LOGIN, GOOGLE_PASSWORD, "/.tmp/cut02.mp3")
    join_audio()
    join_audio_and_video(output_file_name)
    remove_tmp_dir()

    print(f"You can find the result in ./results/{output_file_name}.mp4")
