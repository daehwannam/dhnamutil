
import torch
import torch.nn as nn

from . import rnn_util


class MyModule(nn.Module):
    # @classmethod
    # def set_gpu_usage(cls, gpu_usage):
    #     cls.gpu_usage = gpu_usage

    def __init__(self):
        super().__init__()

        if len(tuple(self.parameters())) == 0:
            # because enable_cuda requires at least one parameter
            self.scalar_parameter = nn.Parameter(torch.zeros(1), requires_grad=False)

    def enable_cuda(self, arg):
        "it should be carefully used because of performance issue."
        return enable_cuda(self, arg)

    def load_state_dict_partially(self, prev_state_dict):
        # https://github.com/pytorch/vision/issues/173
        model_dict = self.state_dict()

        overlap = {k: v for k, v in prev_state_dict.items()
                   if k in model_dict}

        new_state_dict = self.state_dict()
        new_state_dict.update(overlap)
        self.load_state_dict(new_state_dict)

        missing = {k: v for k, v in model_dict.items()
                   if k not in prev_state_dict}
        unexpected = {k: v for k, v in prev_state_dict.items()
                      if k not in model_dict}

        return missing, unexpected

    def get_module_device(self):
        return get_module_device(self)

    def parameters_requiring_grad(self):
        for parameter in self.parameters():
            if parameter.requires_grad:
                yield parameter


def enable_cuda(model, arg):
    "it should be carefully used because of performance issue."
    if is_cuda_enabled(model):
        arg = arg.cuda()
    else:
        arg = arg.cpu()
    return arg


def get_any_parameter(model):
    try:
        return next(model.parameters())
    except StopIteration:
        raise Exception("The model '{}' has no parameter.".format(model.__name__))


def is_cuda_enabled(model):
    return get_any_parameter(model).is_cuda


def get_module_device(model):
    return get_any_parameter(model).device


def make_cuda_on(condition):
    def cuda_on(arg):
        if condition:
            arg = arg.cuda()
        else:
            arg = arg.cpu()
        return arg
    return cuda_on


def create_lstm(*args, **kargs):
    # return rnn_util.LayerNormLSTM(*args, **kargs)  # debug
    if kargs['r_dropout'] > 0 or kargs['layer_norm_enabled']:
        return rnn_util.LayerNormLSTM(*args, **kargs)
    else:
        del kargs['r_dropout'], kargs['layer_norm_enabled']
        if ((len(args) > 2 and args[2] == 1) or kargs['num_layers'] == 1) and kargs['dropout'] > 0:
            kargs['dropout'] = 0
        return nn.LSTM(*args, **kargs)


def create_lstm_cell(*args, **kargs):
    if kargs['dropout'] > 0 or kargs['layer_norm_enabled']:
        return rnn_util.LayerNormLSTMCell(*args, **kargs)
    else:
        del kargs['dropout'], kargs['layer_norm_enabled']
        return nn.LSTMCell(*args, **kargs)


def normalize(tensor):
    return tensor / tensor.sum()


class WeightedTanh(nn.Module):
    def __init__(self, scale_weight=None):
        super().__init__()
        if scale_weight:
            self.scale_weight = scale_weight
        else:
            self.scale_weight = nn.Parameter(torch.ones(1))

    def forward(self, tensor):
        return self.scale_weight * torch.tanh(tensor)


class LinearOnly(nn.Linear):
    def __init__(self, in_features, out_features, bias=False):
        super().__init__(in_features, out_features, bias)


class BilinearOnly(nn.Bilinear):
    def __init__(self, in1_features, in2_features, out_features, bias=False):
        super().__init__(in1_features, in2_features, out_features, bias)


class BilinearFlat(nn.Bilinear):
    def __init__(self, in1_features, in2_features, bias=True):
        super().__init__(in1_features, in2_features, out_features=1, bias=bias)

    def forward(self, input1, input2):
        """
        two input tensors should match their intermediate sizes from k to n-1
        e.g. input1.size() --> (a, b, c, d, e, in1_features)
             input2.size() --> (d, e, in2_features)

             or
             input1.size() --> (b, c, d, e, in1_features)
             input2.size() --> (a, b, c, d, e, in2_features)

             then
             output.size() --> (a, b, c, d, e)

        :param input1: (N,*,H1) or (*,H1)
        :param input2: (N,*,H2) or (*,H2)
        :output: (N,*)
        """
        input1_size = input1.size()
        input2_size = input2.size()

        if len(input1_size) == len(input2_size):
            super_output = super().forward(input1, input2)
        elif len(input1_size) < len(input2_size):
            new_input1 = self.repeat_smaller_tensor(input1, input2)
            super_output = super().forward(new_input1, input2)
        else:
            assert len(input1_size) > len(input2_size)
            new_input2 = self.repeat_smaller_tensor(input2, input1)
            super_output = super().forward(input1, new_input2)

        return super_output.squeeze(-1)

    def repeat_smaller_tensor(self, smaller_tensor, bigger_tensor):
        smaller_size = smaller_tensor.size()
        bigger_size = bigger_tensor.size()

        gap_size = self.compare_sizes(smaller_size, bigger_size)
        multiplier = 1
        for dim in gap_size:
            multiplier *= dim

        try:
            return smaller_tensor.view(-1).repeat(multiplier).view(gap_size + smaller_size)
        except RuntimeError:
            breakpoint()

    def compare_sizes(self, size1, size2):
        assert len(size1) < len(size2)
        for dim1, dim2 in zip(reversed(size1[:-1]), reversed(size2[:-1])):
            assert dim1 == dim2, "Tensors' intermediate dimensions should be different"
        gap_size = size2[: len(size2) - len(size1)]
        return gap_size


class BilinearFlatOnly(BilinearFlat):
    def __init__(self, in1_features, in2_features, bias=False):
        super().__init__(in1_features, in2_features, bias=bias)


class LinearLayerNorm(nn.Module):
    def __init__(self, in_features, out_features):
        super().__init__()

        self.linear = nn.Linear(in_features, out_features, bias=False)
        self.ln = nn.LayerNorm(out_features)

    def forward(self, tensor):
        return self.ln(self.linear(tensor))


def residual(func, x):
    return func(x) + x


def max_over_index(tensor, index):
    max_values, max_indices = tensor.max(index)
    return max_values
