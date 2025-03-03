import os
from datetime import datetime
from typing import Optional

from app.core.task.typing.DirectoryInfo import DirectoryInfo
from typing import Dict
from typing import Optional
from app.core.task.typing.DirectoryInfo import DirectoryInfo
from app.drivers.benchmarks.AbstractBenchmark import AbstractBenchmark
from os.path import join

class DARPA(AbstractBenchmark):
    def __init__(self) -> None:
        self.name = os.path.basename(__file__)[:-3].lower()
        super(DARPA, self).__init__()

    def setup_experiment(
        self, bug_index: int, container_id: Optional[str], test_all: bool
    ) -> bool:

        is_error = True
        if self.install_deps(bug_index, container_id):
            is_error = super(DARPA, self).setup_experiment(
                bug_index, container_id, test_all
            )
        if not is_error:
            if not self.experiment_subjects[bug_index - 1][
                self.key_language
            ] == "java" or self.compress_dependencies(container_id, bug_index):
                pass
                #self.emit_success("dependencies compressed successfully")
                #if self.verify(bug_index, container_id):
                #    self.emit_success("verified successfully")
                    #if self.transform(bug_index, container_id):
                    #    self.emit_success("transformation successful")
                    #else:
                    #    self.emit_error("transformation failed")
                    #    is_error = True
                #else:
                #    self.emit_error("verification failed")
                #    is_error = True
            else:
                self.emit_error("dependency compression failed")
                is_error = True
        return is_error

    def install_deps(self, bug_index: int, container_id: Optional[str]) -> bool:
        self.emit_normal("installing experiment dependencies")
        return True

    def deploy(self, bug_index: int, container_id: Optional[str]) -> bool:
        self.emit_normal("downloading experiment subject")
        experiment_item = self.experiment_subjects[bug_index - 1]
        bug_id = str(experiment_item[self.key_bug_id])
        self.log_deploy_path = (
            self.dir_logs + "/" + self.name + "-" + bug_id + "-deploy.log"
        )
        time = datetime.now()
        command_str = f"bash setup.sh"
        status = self.run_command(
            container_id, command_str, self.log_deploy_path, self.dir_setup
        )
        self.emit_debug(
            "setup took {} second(s)".format((datetime.now() - time).total_seconds())
        )
        return status == 0

    def config(self, bug_index: int, container_id: Optional[str]) -> bool:
        self.emit_normal("configuring experiment subject")
        return True

    def build(self, bug_index: int, container_id: Optional[str]) -> bool:
        self.emit_normal("building experiment subject")
        experiment_item = self.experiment_subjects[bug_index - 1]
        bug_id = str(experiment_item[self.key_bug_id])
        self.log_build_path = (
            self.dir_logs + "/" + self.name + "-" + bug_id + "-build.log"
        )
        time = datetime.now()
        
        if not self.is_file(join(self.dir_setup,'.build_default'),container_id):
            command_str = "bash build.sh"

            status = self.run_command(
                container_id, command_str, self.log_build_path, self.dir_setup
            )
            self.emit_debug(
                "build took {} second(s)".format((datetime.now() - time).total_seconds())
            )
            return status == 0
        else:
            self.emit_normal("Already built. Skipping")
            return True

    def compress_dependencies(
        self, container_id: Optional[str], bug_index: int
    ) -> bool:
        self.emit_normal("compressing experiment dependencies")
        return True

    def test(self, bug_index: int, container_id: Optional[str]) -> bool:
        self.emit_normal("testing experiment subject")
        experiment_item = self.experiment_subjects[bug_index - 1]
        bug_id = str(experiment_item[self.key_bug_id])
        self.log_test_path = (
            self.dir_logs + "/" + self.name + "-" + bug_id + "-test.log"
        )
        time = datetime.now()
        failing_test_list = experiment_item[self.key_failing_test_identifiers]
        failing_status = 1
        if len(failing_test_list) != 0:
            command_str = f"bash test.sh {failing_test_list[0]}"
            failing_status = self.run_command(
                container_id,
                command_str,
                self.log_test_path,
                os.path.join(self.dir_setup),
            )

        passing_test_list = experiment_item[self.key_passing_test_identifiers]
        passing_status = 0
        if len(passing_test_list) != 0:
            command_str = f"bash test.sh {passing_test_list[0]}"
            passing_status = self.run_command(
                container_id,
                command_str,
                self.log_test_path,
                os.path.join(self.dir_setup),
            )

        self.emit_debug(
            "Test took {} second(s)".format((datetime.now() - time).total_seconds())
        )
        return failing_status != 0 and passing_status == 0

    def verify(self, bug_index: int, container_id: Optional[str]) -> bool:
        self.emit_normal("verify dev patch and test-oracle")
        experiment_item = self.experiment_subjects[bug_index - 1]
        bug_id = str(experiment_item[self.key_bug_id])
        self.log_test_path = (
            self.dir_logs + "/" + self.name + "-" + bug_id + "-verify.log"
        )
        time = datetime.now()
        failing_test_list = experiment_item[self.key_failing_test_identifiers]
        command_str = f"bash verify.sh {failing_test_list[0] if len(failing_test_list) != 0 else ''}"
        status = self.run_command(
            container_id, command_str, self.log_test_path, self.dir_setup
        )

        self.emit_debug(
            "verify took {} second(s)".format((datetime.now() - time).total_seconds())
        )
        return status == 0

    def transform(self, bug_index: int, container_id: Optional[str]) -> bool:
        self.emit_normal("transforming source code")
        experiment_item = self.experiment_subjects[bug_index - 1]
        bug_id = str(experiment_item[self.key_bug_id])
        self.log_test_path = (
            self.dir_logs + "/" + self.name + "-" + bug_id + "-transform.log"
        )
        time = datetime.now()
        command_str = "echo 'transformation complete'"
        status = self.run_command(
            container_id, command_str, self.log_test_path, self.dir_setup
        )
        self.emit_debug(
            "transform took {} second(s)".format(
                (datetime.now() - time).total_seconds()
            )
        )
        return status == 0

    def clean(self, exp_dir_path: str, container_id: Optional[str]) -> None:
        self.emit_normal("removing experiment subject")
        command_str = "rm -rf " + exp_dir_path
        self.run_command(container_id, command_str)
        return

    def save_artifacts(
        self, dir_info: DirectoryInfo, container_id: Optional[str]
    ) -> None:
        self.list_artifact_dirs = []  # path should be relative to experiment directory
        self.list_artifact_files = []  # path should be relative to experiment directory
        super(DARPA, self).save_artifacts(dir_info, container_id)
