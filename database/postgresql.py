import logging
import re
from typing import Any, Dict, Iterable, List, Tuple, Union

import psycopg2

from companies import Company, InvalidCNPJException, Partner, CompaniesDatabaseInterface


class PostgreSQLDatabase(CompaniesDatabaseInterface):
    def __init__(self, host, database, user, password, port):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port

    def _select(self, command: str, data: Dict = {}) -> Iterable[Tuple]:
        connection = psycopg2.connect(
            dbname=self.database,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
        )
        with connection.cursor() as cursor:
            cursor.execute(command, data)
            logging.debug(f"Starting query: {cursor.query}")
            for entry in cursor:
                logging.debug(entry)
                yield entry
            logging.debug(f"Finished query: {cursor.query}")

    def get_company(self, cnpj: str = "") -> Union[Company, None]:
        command = """
        SELECT
            *
        FROM
            resposta_cnpj
        WHERE
            estabelecimento_cnpj_basico = %(cnpj_basico)s
            AND estabelecimento_cnpj_ordem = %(cnpj_ordem)s
            AND estabelecimento_cnpj_dv = %(cnpj_dv)s
        ;
        """
        if not self._is_valid_cnpj(cnpj):
            raise InvalidCNPJException(f'CNPJ "{cnpj}" is not valid.')

        cnpj_basico, cnpj_ordem, cnpj_dv = self._split_cnpj(cnpj)
        data = {
            "cnpj_basico": cnpj_basico,
            "cnpj_ordem": cnpj_ordem,
            "cnpj_dv": cnpj_dv,
        }
        result = list(self._select(command, data))
        if result == []:
            return None

        return self._format_company_data(result[0], cnpj)

    def get_partners(self, cnpj: str = "") -> Tuple[int, List[Partner]]:
        command = """
        SELECT
            *
        FROM
            resposta_socios
        WHERE
            cnpj_basico = %(cnpj_basico)s
        ;
        """
        if not self._is_valid_cnpj(cnpj):
            raise InvalidCNPJException(f'CNPJ "{cnpj}" is not valid.')

        cnpj_basico, *_ = self._split_cnpj(cnpj)
        data = {
            "cnpj_basico": cnpj_basico,
        }
        results = list(self._select(command, data))
        return (
            len(results),
            [self._format_partner_data(result, cnpj) for result in results],
        )

    def _format_company_data(self, data: Tuple, cnpj: str) -> Company:
        cnpj_only_digits = self._cnpj_only_digits(cnpj)
        cnpj_basico, cnpj_ordem, cnpj_dv = self._split_cnpj(cnpj)
        full_cnpj = self._format_full_cnpj(cnpj)
        formatted_data = [self._always_str_or_none(value) for value in data]
        return Company(
            cnpj_basico=cnpj_basico,
            cnpj_ordem=cnpj_ordem,
            cnpj_dv=cnpj_dv,
            cnpj_completo=full_cnpj,
            cnpj_completo_apenas_numeros=cnpj_only_digits,
            identificador_matriz_filial=formatted_data[3],
            nome_fantasia=formatted_data[4],
            situacao_cadastral=formatted_data[5],
            data_situacao_cadastral=formatted_data[6],
            motivo_situacao_cadastral=formatted_data[7],
            nome_cidade_exterior=formatted_data[8],
            data_inicio_atividade=formatted_data[9],
            cnae_fiscal_secundario=formatted_data[10],
            tipo_logradouro=formatted_data[11],
            logradouro=formatted_data[12],
            numero=formatted_data[13],
            complemento=formatted_data[14],
            bairro=formatted_data[15],
            cep=formatted_data[16],
            uf=formatted_data[17],
            ddd_telefone_1=formatted_data[18],
            ddd_telefone_2=formatted_data[19],
            ddd_telefone_fax=formatted_data[20],
            correio_eletronico=formatted_data[21],
            situacao_especial=formatted_data[22],
            data_situacao_especial=formatted_data[23],
            pais=formatted_data[24],
            municipio=formatted_data[25],
            razao_social=formatted_data[26],
            natureza_juridica=formatted_data[27],
            qualificacao_do_responsavel=formatted_data[28],
            capital_social=formatted_data[29],
            porte=formatted_data[30],
            ente_federativo_responsavel=formatted_data[31],
            opcao_pelo_simples=formatted_data[32],
            data_opcao_pelo_simples=formatted_data[33],
            data_exclusao_pelo_simples=formatted_data[34],
            opcao_pelo_mei=formatted_data[35],
            data_opcao_pelo_mei=formatted_data[36],
            data_exclusao_pelo_mei=formatted_data[37],
            cnae=formatted_data[38],
        )

    def _format_partner_data(self, data: Tuple, cnpj: str) -> Partner:
        cnpj_only_digits = self._cnpj_only_digits(cnpj)
        cnpj_basico, cnpj_ordem, cnpj_dv = self._split_cnpj(cnpj)
        full_cnpj = self._format_full_cnpj(cnpj)
        formatted_data = [self._always_str_or_none(value) for value in data]
        return Partner(
            cnpj_basico=cnpj_basico,
            cnpj_ordem=cnpj_ordem,
            cnpj_dv=cnpj_dv,
            cnpj_completo=full_cnpj,
            cnpj_completo_apenas_numeros=cnpj_only_digits,
            identificador_socio=formatted_data[1],
            razao_social=formatted_data[2],
            cnpj_cpf_socio=formatted_data[3],
            qualificacao_socio=formatted_data[4],
            data_entrada_sociedade=formatted_data[5],
            pais_socio_estrangeiro=formatted_data[6],
            numero_cpf_representante_legal=formatted_data[7],
            nome_representante_legal=formatted_data[8],
            qualificacao_representante_legal=formatted_data[9],
            faixa_etaria=formatted_data[10],
        )

    def _always_str_or_none(self, data: Any) -> Union[str, None]:
        if data == "None" or data == "" or data is None:
            return None
        elif not isinstance(data, str):
            return str(data)
        else:
            return data

    def _is_valid_cnpj(self, cnpj: str) -> bool:
        cnpj_only_digits = self._cnpj_only_digits(cnpj)
        if cnpj_only_digits == "" or len(cnpj_only_digits) > 14:
            return False

        cnpj_without_dv = cnpj_only_digits[:-2]
        generated_dv = self._generate_cnpj_dv(cnpj_without_dv)
        return cnpj_only_digits[-2:] == generated_dv

    def _cnpj_only_digits(self, cnpj: str) -> str:
        only_digits = re.sub(r"[^\d]", "", cnpj)
        if only_digits == "":
            return only_digits
        else:
            return only_digits.zfill(14)

    def _generate_cnpj_dv(self, cnpj_without_dv: str) -> str:
        first_digit = self._calculate_cnpj_dv_digit(cnpj_without_dv)
        second_digit = self._calculate_cnpj_dv_digit(
            cnpj_without_dv, first_digit=first_digit
        )
        return first_digit + second_digit

    def _calculate_cnpj_dv_digit(
        self, cnpj_without_dv: str, first_digit: str = ""
    ) -> str:
        weights = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
        if first_digit == "":
            weights = weights[1:]

        cnpj_to_weight = cnpj_without_dv + first_digit
        weighted_digits = [
            int(num) * weight for num, weight in zip(cnpj_to_weight, weights)
        ]
        sum_remainder = sum(weighted_digits) % 11

        if sum_remainder < 2:
            return "0"
        else:
            return str(11 - sum_remainder)

    def _format_full_cnpj(self, cnpj: str) -> str:
        cnpj_only_digits = self._cnpj_only_digits(cnpj)
        mask = "{}.{}.{}/{}-{}"
        return mask.format(
            cnpj_only_digits[:2],
            cnpj_only_digits[2:5],
            cnpj_only_digits[5:8],
            cnpj_only_digits[8:12],
            cnpj_only_digits[12:],
        )

    def _split_cnpj(self, cnpj: str) -> Tuple[str, str, str]:
        cnpj_only_digits = self._cnpj_only_digits(cnpj)
        return cnpj_only_digits[:8], cnpj_only_digits[8:12], cnpj_only_digits[12:]

    def _unsplit_cnpj(self, cnpj_basico: str, cnpj_ordem: str, cnpj_dv: str) -> str:
        mask = "{cnpj_basico}{cnpj_ordem}{cnpj_dv}"
        return mask.format(
            cnpj_basico=str(cnpj_basico).zfill(8),
            cnpj_ordem=str(cnpj_ordem).zfill(4),
            cnpj_dv=str(cnpj_dv).zfill(2),
        )