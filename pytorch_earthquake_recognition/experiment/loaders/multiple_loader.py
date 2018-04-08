from loaders.base_loader import SpectrogramBaseDataset




class SpectrogramMultipleDataset(SpectrogramBaseDataset):
    """
    """

    def __init__(self, img_path, transform=None, test=False, divide_test=.3, **kwargs):   # 30%
        super().__init__(img_path, transform, test, divide_test=divide_test, **kwargs)


if __name__ == '__main__':
    IMG_PATH = '../spectrograms'
    s = SpectrogramMultipleDataset(IMG_PATH)
    s = iter(s)
    print(next(s))