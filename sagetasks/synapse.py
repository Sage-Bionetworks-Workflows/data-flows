"""Collection of Synapse-related Prefect tasks
"""

import os
from tempfile import TemporaryDirectory

from prefect import Task
import synapseclient
import pandas as pd


CONTENT_TYPES = {
    ",": "text/csv",
    "\t": "text/tab-separated-values"
}


class SynapseBaseTask(Task):

    @property
    def synapse(self):
        return synapseclient.login(authToken=self.auth_token, silent=True)

    def run(self, auth_token):
        self.auth_token = auth_token
        raise NotImplementedError("The `run` method hasn't implemented.")


class SynapseGetDataFrameTask(SynapseBaseTask):

    def run(self, auth_token, synapse_id, sep=None):
        self.auth_token = auth_token
        file = self.synapse.get(synapse_id, downloadFile=False)
        file_handle_id = file._file_handle.id
        file_handle_url = self.synapse.restGET(
            f"/file/{file_handle_id}",
            self.synapse.fileHandleEndpoint,
            params={"redirect": False,
                    "fileAssociateType": "FileEntity",
                    "fileAssociateId": file.id.replace("syn", "")}
        )
        data_frame = pd.read_table(file_handle_url, sep=sep)
        return data_frame

class SynapseStoreDataFrameTask(SynapseBaseTask):

    def run(self, auth_token, data_frame, name, parent_id, sep=","):
        self.auth_token = auth_token
        with TemporaryDirectory() as dirname:
            fpath = os.path.join(dirname, name)
            content_type = CONTENT_TYPES.get(sep, None)
            with open(fpath, "w") as f:
                data_frame.to_csv(f, sep=sep, index=False)
            syn_file = synapseclient.File(fpath, name=name, parent=parent_id,
                                          contentType=content_type)
            syn_file = self.synapse.store(syn_file)
            os.remove(fpath)
        return syn_file
