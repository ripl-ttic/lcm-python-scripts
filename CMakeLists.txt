cmake_minimum_required(VERSION 2.6.0)

# pull in the pods macros. See cmake/pods.cmake for documentation
set(POD_NAME python-scripts)
include(cmake/pods.cmake)

# require python
find_package(PythonInterp REQUIRED)

# install all python files in the python/ subdirectory
pods_install_python_packages(${CMAKE_CURRENT_SOURCE_DIR}/python)

# install a script "hello-python" that runs the hello.main python module
# This script gets installed to ${CMAKE_INSTALL_PREFIX}/bin/hello-python
# and automatically sets the correct python path.

#pods_install_python_script(floor-change utils.floor_change)

#pods_install_python_script(save-pose-val log_analysis.save_pose_values)

#pods_install_python_script(plot-control log_analysis.plot_control)

#pods_install_python_script(voice-recorder audio_speech.voice_recorder)

#pods_install_python_script(fetch-responses audio_speech.fetch_speech_files)

#pods_install_python_script(speech-synthesizer audio_speech.speech_sythesizer)

#pods_install_python_script(audio2summit audio_speech.er_audio_lcm)

#pods_install_python_script(audio2lcm audio_speech.audio2lcm)

#pods_install_python_script(lcm2audio audio_speech.lcm2audio)
