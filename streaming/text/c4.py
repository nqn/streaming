# Copyright 2022 MosaicML Streaming authors
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, Optional

from transformers.models.auto.tokenization_auto import AutoTokenizer

from streaming.base import Dataset


class C4(Dataset):
    """C4 (Colossal Cleaned Common Crawl) dataset.

    Args:
        tokenizer_name (str): The name of the HuggingFace tokenizer to use to tokenize samples.
        max_seq_len (int): The max sequence length of each token sample.
        group_method (str): How to group text samples into token samples. Currently only supporting
            ``'truncate'``.
        local (str): Local dataset directory where shards are cached by split.
        remote (str, optional): Download shards from this remote path or directory. If None, this
            rank and worker's partition of the dataset must all exist locally. Defaults to
            ``None``.
        split (str, optional): Which dataset split to use, if any. Defaults to ``None``.
        shuffle (bool): Whether to shuffle the samples while iterating. Defaults to ``True``.
        prefetch (int, optional): Target number of samples remaining to prefetch while iterating.
            Defaults to ``None``.
        keep_zip (bool, optional): Whether to keep or delete the compressed file when
            decompressing downloaded shards. If set to None, keep iff remote is local. Defaults to
            ``None``.
        retry (int): Number of download re-attempts before giving up. Defaults to ``2``.
        timeout (float): Number of seconds to wait for a shard to download before raising an
            exception. Defaults to ``60``.
        hash (str, optional): Optional hash or checksum algorithm to use to validate shards.
            Defaults to ``None``.
        batch_size (int, optional): Hint the batch_size that will be used on each device's
            DataLoader. Defaults to ``None``.
    """

    def __init__(self,
                 tokenizer_name: str,
                 max_seq_len: int,
                 group_method: str,
                 local: str,
                 remote: Optional[str] = None,
                 split: Optional[str] = None,
                 shuffle: bool = True,
                 prefetch: Optional[int] = 100_000,
                 keep_zip: Optional[bool] = None,
                 retry: int = 2,
                 timeout: float = 60,
                 hash: Optional[str] = None,
                 batch_size: Optional[int] = None) -> None:
        if group_method not in ['truncate']:
            raise ValueError(f'Only group_method="truncate" is supported at this time.')

        super().__init__(local, remote, split, shuffle, prefetch, keep_zip, retry, timeout, hash,
                         batch_size)
        self.tokenizer_name = tokenizer_name
        self.max_seq_len = max_seq_len
        self.group_method = group_method

        # Build tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_name)  # pyright: ignore
        if self.tokenizer.pad_token is None:
            # Some tokenizers (e.g. GPT2 tokenizer) have no padding token which causes bugs
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def _tokenize(self, text_sample: Dict[str, Any]):
        """Apply the tokenizer to a sample.

        Args:
            text_sample (Dict[str, Any]): Sample to tokenize.
        """
        if self.group_method == 'truncate':
            truncation = True
            padding = 'max_length'
            max_length = self.max_seq_len
        else:
            truncation = False
            padding = False
            max_length = None
        return self.tokenizer(text_sample['text'],
                              truncation=truncation,
                              padding=padding,
                              max_length=max_length)

    def __getitem__(self, idx: int) -> Any:
        """Get sample by global index, blocking to load its shard if missing.

        Args:
            idx (int): Sample index.

        Returns:
            Any: Sample data.
        """
        text_sample = super().__getitem__(idx)
        token_sample = self._tokenize(text_sample)
        # Skip any token grouping, currently only supporting group_method='truncate'
        return token_sample
